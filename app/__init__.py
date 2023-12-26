import os
import redis
import functools
from dotenv import load_dotenv
import google.generativeai as genai
from sqlalchemy.orm import DeclarativeBase
from redis.exceptions import ResponseError
from redis.commands.search.field import TextField
from werkzeug.utils import import_string, find_modules

from flask import Flask
from flask_caching import Cache
from flask_minify import Minify
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


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
    # initialize plugins
    initialize_plugins(app)
    # register blueprints
    register_blueprints(app)
    # initialize generative AI
    setup_generative_ai(app)

    with app.app_context():
        # create db tables if they don't exist
        db.create_all()
        # initialize search index
        initialize_search_index(app)

        from app.cron.handlers import populate_search_index

        # populate search index if empty
        populate_search_index(app)

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


def initialize_search_index(app: Flask) -> None:
    """
    Create a search index if not already created
    and save the object in the app config.
    """

    redis_client = redis.Redis(
        host=app.config["REDIS_HOST"],
        port=app.config["REDIS_PORT"],
        username=app.config["REDIS_USERNAME"],
        password=app.config["REDIS_PASSWORD"],
    )

    schema = (
        TextField("title", weight=2.0),
        TextField("description"),
        TextField("tags"),
    )

    search_index = redis_client.ft("search_index")

    try:
        search_index.create_index(schema)
    except ResponseError:
        pass

    app.config["search_index"] = search_index


def setup_generative_ai(app: Flask) -> None:
    """
    Place generative ai ready partial method in the app config
    that requires just the prompt.
    """
    GEMINI_API_KEY = app.config["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
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
