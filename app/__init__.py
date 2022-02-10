# import os
import os
import json
import atexit
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.config import Config
from elasticsearch import Elasticsearch
from logging.config import dictConfig
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
# search = Search()
migrate = Migrate()
login_manager = LoginManager()
# where the user will be redirected if she's not logged in
login_manager.login_view = 'main.home'
# the class/category of the flash message when the user is not logged in
login_manager.login_message_category = 'warning'


def create_app(config_class=Config):
    # config logger
    # https://flask.palletsprojects.com/en/2.0.x/logging/
    # with open(os.getenv('LOG_CONFIG'), 'r') as j:
    #     dictConfig(json.load(j))

    # create application object
    app = Flask(__name__)
    app.config.from_object(config_class)

    # set up elasticsearch object
    elastic_url = app.config['ELASTIC_URL']
    elastic_name = app.config['ELASTIC_USERNAME']
    elastic_pass = app.config['ELASTIC_PASSWORD']
    http_auth = (elastic_name, elastic_pass)
    app.elasticsearch = Elasticsearch(elastic_url, http_auth=http_auth)

    # set up scheduler object
    app.scheduler = BackgroundScheduler(timezone=app.config['TIMEZONE'])
    app.scheduler.start()
    atexit.register(lambda: app.scheduler.shutdown())

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True, compare_type=True)
    login_manager.init_app(app)

    from app.users.routes import users
    from app.posts.routes import posts
    from app.main.routes import main
    from app.search.routes import search
    from app.cron.routes import cron
    from app.auth.routes import auth
    from app.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)
    app.register_blueprint(search)
    app.register_blueprint(cron)
    app.register_blueprint(auth)
    app.register_blueprint(errors)

    return app
