import os
from dotenv import load_dotenv


class Config:
    load_dotenv()
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SCOPPED_SESSION_DB_URI = os.environ.get('SCOPPED_SESSION_DB_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_OAUTH_SCOPES = os.environ.get('GOOGLE_SCOPES')
    GOOGLE_DISCOVERY_URL = os.environ.get('GOOGLE_DISCOVERY_URL')
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
    ADMIN_OPENID = os.environ.get('ADMIN_OPENID')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
