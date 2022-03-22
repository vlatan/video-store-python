import os
import json
from dotenv import load_dotenv


class Config:
    # load the enviroment variables
    load_dotenv()

    # app
    APP_NAME = os.getenv('APP_NAME')
    DOMAIN = os.getenv('DOMAIN')
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = True if os.getenv('DEBUG') == 'True' else False
    ENV = 'development' if DEBUG else 'production'
    LOG_FILE = os.getenv('LOG_FILE')

    # cache
    CACHE_TYPE = 'SimpleCache'  # Flask-Caching related configs
    CACHE_DEFAULT_TIMEOUT = 300

    # Admin Google openid
    ADMIN_OPENID = os.getenv('ADMIN_OPENID')

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Elasticsearch
    ELASTIC_URL = os.getenv('ELASTIC_URL')
    ELASTIC_USERNAME = os.getenv('ELASTIC_USERNAME')
    ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')

    # Other
    POSTS_PER_PAGE = int(os.getenv('POSTS_PER_PAGE'))
    NUM_RELATED_POSTS = int(os.getenv('NUM_RELATED_POSTS'))

    # Facebook authentication
    FB_CLIENT_ID = os.getenv('FB_CLIENT_ID')
    FB_CLIENT_SECRET = os.getenv('FB_CLIENT_SECRET')

    # Google/Youtube authentication
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_SCOPES = json.loads(os.getenv('GOOGLE_SCOPES'))
    GOOGLE_CLIENT_CONFIG = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "doxder",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [
                "http://localhost:5000/authorize/google",
                "https://localhost:5000/authorize/google",
                f"https://{DOMAIN}/authorize/google"
            ],
            "javascript_origins": [
                "http://localhost",
                "http://localhost:5000",
                "https://localhost",
                "https://localhost:5000",
                f"https://{DOMAIN}"
            ]
        }
    }
