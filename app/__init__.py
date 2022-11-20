import os
from dotenv import load_dotenv
from flask import Flask
from flask_caching import Cache
from flask_minify import Minify
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import import_string
from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, open_dir, exists_in


# load the enviroment variables from an .env file
load_dotenv()
# get config type/class from the environment
CONFIG_TYPE = os.getenv("CONFIG_TYPE")
# import and instantiate the class
cfg = import_string(CONFIG_TYPE)()


cache_cfg = {
    "CACHE_TYPE": cfg.CACHE_TYPE,
    "CACHE_DEFAULT_TIMEOUT": cfg.CACHE_DEFAULT_TIMEOUT,
    "CACHE_REDIS_URL": cfg.CACHE_REDIS_URL,
}
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
    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    minify.init_app(app)
    login_manager.init_app(app)

    # import blueprints
    from app.main.routes import main
    from app.users.routes import users
    from app.posts.routes import posts
    from app.pages.routes import pages
    from app.sources.routes import sources
    from app.search.routes import search
    from app.admin.routes import admin
    from app.auth.routes import auth
    from app.cron.handlers import cron
    from app.sitemap.routes import sitemap
    from app.errors.handlers import errors

    # register blueprints
    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(pages)
    app.register_blueprint(sources)
    app.register_blueprint(search)
    app.register_blueprint(admin)
    app.register_blueprint(auth)
    app.register_blueprint(cron)
    app.register_blueprint(sitemap)
    app.register_blueprint(errors)

    # initialize search index
    index = os.path.abspath("index")
    os.mkdir(index) if not os.path.exists(index) else None
    id_num = ID(unique=True, stored=True)
    schema = Schema(id=id_num, title=TEXT, description=TEXT, tags=TEXT)
    app.index = open_dir(index) if exists_in(index) else create_in(index, schema)

    # import background tasks functions
    from app.cron.handlers import init_scheduler_jobs, populate_search_index

    # work within app context
    with app.app_context():
        db.create_all()  # create the tables if they don't exist
        populate_search_index()  # populate search index if empty
        init_scheduler_jobs()  # initialize scheduled video posting job

    return app
