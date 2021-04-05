# import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from doxapp.config import Config

db = SQLAlchemy()
login_manager = LoginManager()
# where the user will be redirected if she's not logged in
login_manager.login_view = 'main.home'
# the class/category of the flash message when the user is not logged in
login_manager.login_message_category = 'warning'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from doxapp.users.routes import users
    from doxapp.posts.routes import posts
    from doxapp.main.routes import main
    from doxapp.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    return app
