import os
from dotenv import load_dotenv
from flask import Flask
from flask_caching import Cache
from flask_minify import Minify
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import import_string, find_modules
from whoosh.fields import Schema, TEXT, ID
from whoosh.filedb.filestore import FileStorage


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

# instantiate flask plugins
cache = Cache(config=cache_cfg)
db = SQLAlchemy()
migrate = Migrate(render_as_batch=True, compare_type=True)
minify = Minify()
login_manager = LoginManager()

# where the user will be redirected if she's not logged in
login_manager.login_view = "main.home"
# the class/category of the flash message when the user is not logged in
login_manager.login_message_category = "warning"


def create_app():
    """Create a new app instance."""

    # create application object
    app = Flask(__name__)
    # load config
    app.config.from_object(cfg)

    # initialize plugins
    initialize_plugins(app)
    # register blueprints
    register_blueprints(app)
    # initialize search index
    initialize_search_index(app)

    # import background jobs functions
    from app.cron.handlers import init_scheduler_jobs, populate_search_index

    with app.app_context():
        db.create_all()  # create db tables if they don't exist
        populate_search_index()  # populate search index if empty
        init_scheduler_jobs()  # initialize scheduled video posting job

    return app


def initialize_plugins(app):
    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    minify.init_app(app)
    login_manager.init_app(app)


def register_blueprints(app):
    for module in find_modules("app", recursive=True):
        try:
            app.register_blueprint(import_string(f"{module}.bp"))
        except ImportError:
            pass


def initialize_search_index(app):
    indexdir = os.path.abspath("index")
    storage = FileStorage(indexdir).create()
    id_num = ID(unique=True, stored=True)
    schema = Schema(id=id_num, title=TEXT, description=TEXT, tags=TEXT)
    app.index = (
        storage.open_index(schema=schema)
        if storage.index_exists()
        else storage.create_index(schema)
    )
