import os
import json
from dotenv import load_dotenv


class Config:
    # load the enviroment variables
    load_dotenv()

    # Flask app secret key
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Admin Google openid
    ADMIN_OPENID = os.environ.get('ADMIN_OPENID')

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SCOPPED_SESSION_DB_URI = os.environ.get('SCOPPED_SESSION_DB_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Elasticsearch
    ELASTIC_URL = os.environ.get('ELASTIC_URL')
    ELASTIC_USERNAME = os.environ.get('ELASTIC_USERNAME')
    ELASTIC_PASSWORD = os.environ.get('ELASTIC_PASSWORD')

    # Other
    POSTS_PER_PAGE = int(os.environ.get('POSTS_PER_PAGE'))
    NUM_RELATED_POSTS = int(os.environ.get('NUM_RELATED_POSTS'))
    APP_NAME = os.environ.get('APP_NAME')

    # Facebook authentication
    FB_CLIENT_ID = os.environ.get('FB_CLIENT_ID')
    FB_CLIENT_SECRET = os.environ.get('FB_CLIENT_SECRET')

    # Google/Youtube authentication
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_SCOPES = json.loads(os.environ.get('GOOGLE_SCOPES'))
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
                "https://localhost:5000/authorize/google"
            ],
            "javascript_origins": [
                "http://localhost",
                "http://localhost:5000",
                "https://localhost",
                "https://localhost:5000"
            ]
        }
    }
