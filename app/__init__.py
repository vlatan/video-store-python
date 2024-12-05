import os
import json
import logging
import functools
import threading
from redis import Redis
from dotenv import load_dotenv
from collections import OrderedDict
import google.generativeai as genai
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import OperationalError
from redis.exceptions import ResponseError
from redis.commands.search.field import TextField
from werkzeug.utils import import_string, find_modules

from flask import Flask
from flask_caching import Cache
from flask_minify import Minify
from flask.ctx import AppContext
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask.logging import default_handler


# load the enviroment variables from an .env file
load_dotenv()
# get config type/class from the environment
CONFIG_TYPE = os.getenv("CONFIG_TYPE", default="config.DevConfig")
# import and instantiate the class
cfg = import_string(CONFIG_TYPE)()

# flask-caching config
cache_cfg = {
    "CACHE_TYPE": cfg.CACHE_TYPE,
    "CACHE_DEFAULT_TIMEOUT": cfg.CACHE_DEFAULT_TIMEOUT,
    "CACHE_REDIS_URL": cfg.CACHE_REDIS_URL,
}


# SQLAlchemy declarative base class
class Base(DeclarativeBase):
    pass


# instantiate flask plugins
cache = Cache(config=cache_cfg)
db = SQLAlchemy(model_class=Base)
migrate = Migrate(render_as_batch=True, compare_type=True)
minify = Minify()
login_manager = LoginManager()

# where the user will be redirected if she's not logged in
login_manager.login_view = "main.home"  # type: ignore
# the class/category of the flash message when the user is not logged in
login_manager.login_message_category = "warning"


def create_app() -> Flask:
    """Create a new app instance."""

    # create application object
    app = Flask(__name__, instance_relative_config=True)
    # load config
    app.config.from_object(cfg)

    # setup custom config
    app.logger.setLevel(logging.INFO)
    default_handler.setFormatter(CustomFormatter())

    # initialize plugins
    initialize_plugins(app)
    # register blueprints
    register_blueprints(app)
    # initialize generative AI
    setup_generative_ai(app)
    # init a simple redis client
    init_redis_client(app)

    with app.app_context():
        try:
            # create db tables if they don't exist
            db.create_all()
            # initialize search index
            initialize_search_index(app)
            # populate search index if empty
            populate_search_index(app)
        except OperationalError as err:
            app.logger.error(err)

    return app


def initialize_plugins(app: Flask) -> None:
    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    minify.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app: Flask) -> None:
    for module in find_modules("app", recursive=True):
        try:
            app.register_blueprint(import_string(f"{module}.bp"))
        except ImportError:
            pass


def setup_generative_ai(app: Flask) -> None:
    """
    Place generative ai ready partial method in the app config
    that requires just the prompt.
    """
    # limit GRPC library to log only errors
    os.environ["GRPC_VERBOSITY"] = "ERROR"
    genai.configure(api_key=app.config["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")

    # create partial function by supplying safety_settings
    generate_content = functools.partial(
        model.generate_content,
        safety_settings={
            "HARM_CATEGORY_HATE_SPEECH": "block_none",
            "HARM_CATEGORY_HARASSMENT": "block_none",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "block_none",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "block_none",
        },
    )

    # place the func object in the app config
    app.config["generate_content"] = generate_content


def init_redis_client(app: Flask) -> None:
    redis_client_url = app.config["CACHE_REDIS_URL"]
    app.config["REDIS_CLIENT"] = Redis().from_url(redis_client_url)


def initialize_search_index(app: Flask) -> None:
    """
    Create a search index if not already created
    and save the object in the app config.
    """

    redis_client = app.config["REDIS_CLIENT"]

    schema = (
        TextField("video_id"),
        TextField("title", weight=2.0),
        TextField("description"),
        TextField("tags"),
        TextField("thumbnail"),
        TextField("srcset"),
    )

    search_index = redis_client.ft("search_index")

    # try:
    #     search_index.dropindex(delete_documents=True)
    # except ResponseError:
    #     pass

    try:
        search_index.create_index(schema)
    except ResponseError:
        pass

    app.config["SEARCH_INDEX"] = search_index


def populate_search_index(app: Flask) -> None:
    """Populate the app search index."""

    thread_name = "search_index"
    for thread in threading.enumerate():
        if thread.name == thread_name:
            return

    # reindex the app in a thread, send app context in the thread
    thread = threading.Thread(
        target=reindex,
        name=thread_name,
        args=[app.app_context()],
    )

    thread.start()


def reindex(app_context: AppContext) -> None:
    if not app_context:
        return

    from app.models import Post

    with app_context:
        Post.reindex()


class CustomFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            OrderedDict(
                time=self.formatTime(record),
                level=record.levelname,
                message=record.getMessage(),
            )
        )
