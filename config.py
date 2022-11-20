import os
import json


class Config:
    # app
    APP_NAME = os.getenv("APP_NAME")
    APP_DESCRIPTION = os.getenv("APP_DESCRIPTION")
    DOMAIN = os.getenv("DOMAIN")
    SECRET_KEY = os.getenv("SECRET_KEY")
    GTAG_ID = os.getenv("GTAG_ID")
    CRON_HOUR = int(os.getenv("CRON_HOUR"))

    # Flask-Caching
    CACHE_TYPE = os.getenv("CACHE_TYPE")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT"))
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL")

    # Admin Google openid
    ADMIN_OPENID = os.getenv("ADMIN_OPENID")

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Other
    POSTS_PER_PAGE = int(os.getenv("POSTS_PER_PAGE"))
    NUM_RELATED_POSTS = int(os.getenv("NUM_RELATED_POSTS"))

    # Facebook authentication
    FB_CLIENT_ID = os.getenv("FB_CLIENT_ID")
    FB_CLIENT_SECRET = os.getenv("FB_CLIENT_SECRET")
    FB_GRAPH_ENDPOINT = "https://graph.facebook.com/v12.0"
    FB_DIALOG_ENDPOINT = "https://www.facebook.com/v12.0/dialog/oauth"
    FB_ACCESS_TOKEN_ENDPOINT = os.path.join(FB_GRAPH_ENDPOINT, "oauth", "access_token")
    FB_INSPECT_TOKEN_ENDPOINT = "https://graph.facebook.com/debug_token"

    # Google/Youtube authentication
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_SCOPES = json.loads(os.getenv("GOOGLE_SCOPES"))
    GOOGLE_REDIRECT_URIS = json.loads(os.getenv("GOOGLE_REDIRECT_URIS"))
    GOOGLE_JS_ORIGINS = json.loads(os.getenv("GOOGLE_JAVASCRIPT_ORIGINS"))
    GOOGLE_CLIENT_CONFIG = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": GOOGLE_PROJECT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": GOOGLE_REDIRECT_URIS,
            "javascript_origins": GOOGLE_JS_ORIGINS,
        }
    }


class DevConfig(Config):
    DEBUG = True
    TESTING = True


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
