import os
from dotenv import load_dotenv


class Config:
    load_dotenv()
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SCOPPED_SESSION_DB_URI = os.environ.get('SCOPPED_SESSION_DB_URI')
    # neeeds to be True if MSEARCH_ENABLE = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MSEARCH_ENABLE = True
    MSEARCH_INDEX_NAME = os.environ.get('MSEARCH_INDEX_NAME')
    MSEARCH_BACKEND = os.environ.get('MSEARCH_BACKEND')
    MSEARCH_PRIMARY_KEY = os.environ.get('MSEARCH_PRIMARY_KEY')
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_OAUTH_SCOPES = os.environ.get('GOOGLE_SCOPES')
    GOOGLE_DISCOVERY_URL = os.environ.get('GOOGLE_DISCOVERY_URL')
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    ADMIN_OPENID = os.environ.get('ADMIN_OPENID')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    ELASTICSEARCH = {"hosts": [ELASTICSEARCH_URL]}
    POSTS_PER_PAGE = int(os.environ.get('POSTS_PER_PAGE'))
    NUM_RELATED_POSTS = int(os.environ.get('NUM_RELATED_POSTS'))

    GOOGLE_OAUTH_CLIENT_CONFIG = {
        "web": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "project_id": "doxder",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uris": [
                "http://localhost:5000/login/google/authorized",
                "http://localhost:5000/oauth2callback",
                "http://localhost:5000/oauth"
            ],
            "javascript_origins": [
                "http://localhost",
                "http://localhost:5000"
            ]
        }
    }
