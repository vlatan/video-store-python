import os
import sys
import logging
import atexit
import signal
from pytz import utc
from flask import Flask
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.config import Config
from elasticsearch import Elasticsearch
from apscheduler.schedulers.background import BackgroundScheduler

cache = Cache()
db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()
# where the user will be redirected if she's not logged in
login_manager.login_view = 'main.home'
# the class/category of the flash message when the user is not logged in
login_manager.login_message_category = 'warning'

# config logger
# logging.basicConfig(filename=os.getenv('LOG_FILE'), level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('elasticsearch').setLevel(logging.INFO)


def create_app(default_config=Config):
    """Create a new app instance."""

    # create application object
    app = Flask(__name__)
    app.config.from_object(default_config)

    # configure elasticsearch
    elastic_url = app.config['ELASTIC_URL']
    elastic_name = app.config['ELASTIC_USERNAME']
    elastic_pass = app.config['ELASTIC_PASSWORD']
    http_auth = (elastic_name, elastic_pass)
    app.elasticsearch = Elasticsearch(elastic_url, http_auth=http_auth)

    cache.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True, compare_type=True)
    login_manager.init_app(app)

    from app.users.routes import users
    from app.posts.routes import posts
    from app.main.routes import main
    from app.search.routes import search
    from app.auth.routes import auth
    from app.cron.handlers import cron
    from app.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)
    app.register_blueprint(search)
    app.register_blueprint(auth)
    app.register_blueprint(cron)
    app.register_blueprint(errors)

    # configure scheduler
    app.scheduler = BackgroundScheduler(timezone=utc, daemon=False)

    def kill_scheduler(signum=None, frame=None):
        try:
            app.scheduler.shutdown(wait=False)
        finally:
            exit(0)

    signal.signal(signal.SIGTERM, kill_scheduler)
    signal.signal(signal.SIGINT, kill_scheduler)

    with app.app_context():
        from app.cron.handlers import init_scheduler_jobs
        app.scheduler.start()
        init_scheduler_jobs()

    return app
