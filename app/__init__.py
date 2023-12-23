import os
import functools
from dotenv import load_dotenv
from celery import Celery, Task
import google.generativeai as genai
from sqlalchemy.orm import DeclarativeBase
from whoosh.fields import Schema, TEXT, ID
from whoosh.filedb.filestore import FileStorage
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
        # make avatars directory if it doesn't exist
        make_dirs(app)
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
    indexdir = os.path.abspath("index")
    storage = FileStorage(indexdir).create()
    id_num = ID(unique=True, stored=True)
    schema = Schema(id=id_num, title=TEXT, description=TEXT, tags=TEXT)
    app.config["search_index"] = (
        storage.open_index(schema=schema)
        if storage.index_exists()
        else storage.create_index(schema)
    )


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


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
        safety_settings={"HATE_SPEECH": "block_none", "HARASSMENT": "block_none"},
    )

    # place the func object in the app config
    app.config["generate_content"] = generate_content


def make_dirs(app: Flask) -> None:
    volume = app.config["VOLUME_MOUNT_PATH"]
    root = volume if volume else app.root_path
    avatars_dir = os.path.join(root, "static", "images", "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
