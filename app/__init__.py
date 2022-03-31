import os.path
from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_minify import Minify
from app.config import Config
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID

cache = Cache()
db = SQLAlchemy()
migrate = Migrate(render_as_batch=True, compare_type=True)
minify = Minify()
login_manager = LoginManager()

# where the user will be redirected if she's not logged in
login_manager.login_view = 'main.home'
# the class/category of the flash message when the user is not logged in
login_manager.login_message_category = 'warning'


def create_app(default_config=Config):
    """Create a new app instance."""

    # create application object
    app = Flask(__name__)
    # load config
    app.config.from_object(default_config)

    # initialize search index
    os.mkdir('index') if not os.path.exists('index') else None
    id_num = ID(unique=True, stored=True)
    schema = Schema(id=id_num, title=TEXT, description=TEXT, tags=TEXT)
    exists = exists_in('index')
    app.index = open_dir('index') if exists else create_in('index', schema)

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
    from app.lists.routes import lists
    from app.search.routes import search
    from app.auth.routes import auth
    from app.cron.handlers import cron
    from app.sitemap.routes import sitemap
    from app.errors.handlers import errors

    # register blueprints
    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(pages)
    app.register_blueprint(lists)
    app.register_blueprint(search)
    app.register_blueprint(auth)
    app.register_blueprint(cron)
    app.register_blueprint(sitemap)
    app.register_blueprint(errors)

    with app.app_context():
        db.create_all()

    return app
