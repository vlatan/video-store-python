import os
import json
import base64
import sqlalchemy


def load_env(var):
    """
    Fetch and JSON decode the value from environment variable.
    If var doesn't exist or its value is empty string return None.
    If var value is not a valid JSON document return the value as string.
    """
    result = os.getenv(var)
    try:
        parse_nums = {"parse_float": float, "parse_int": int}
        return json.loads(result, **parse_nums) if result else None
    except (TypeError, json.decoder.JSONDecodeError):
        return result


class Config:
    # App settings
    APP_NAME = load_env("APP_NAME")
    APP_DESCRIPTION = load_env("APP_DESCRIPTION")
    DOMAIN = load_env("DOMAIN")
    SECRET_KEY = load_env("SECRET_KEY")
    GTAG_ID = load_env("GTAG_ID")
    POSTS_PER_PAGE = load_env("POSTS_PER_PAGE") or 24
    NUM_RELATED_POSTS = load_env("NUM_RELATED_POSTS") or 5
    SEND_FILE_MAX_AGE_DEFAULT = load_env("SEND_FILE_MAX_AGE_DEFAULT") or 315360000

    # ======================================== #

    # FB APIs settings
    FB_CLIENT_ID = str(load_env("FB_CLIENT_ID"))
    FB_CLIENT_SECRET = load_env("FB_CLIENT_SECRET")
    FB_GRAPH_ENDPOINT = "https://graph.facebook.com/v12.0"
    FB_DIALOG_ENDPOINT = "https://www.facebook.com/v12.0/dialog/oauth"
    FB_ACCESS_TOKEN_ENDPOINT = os.path.join(FB_GRAPH_ENDPOINT, "oauth", "access_token")
    FB_INSPECT_TOKEN_ENDPOINT = "https://graph.facebook.com/debug_token"

    # ======================================== #

    # Google APIs settings
    ADMIN_OPENID = str(load_env("ADMIN_OPENID"))
    YOUTUBE_API_KEY = load_env("YOUTUBE_API_KEY")
    GEMINI_API_KEY = load_env("GEMINI_API_KEY")
    GEMINI_MODEL = load_env("GEMINI_MODEL") or "gemini-2.5-flash"
    GOOGLE_OAUTH_SCOPES = load_env("GOOGLE_OAUTH_SCOPES")
    _GOOGLE_OAUTH_CLIENT_BASE64 = load_env("GOOGLE_OAUTH_CLIENT") or ""
    GOOGLE_OAUTH_CLIENT = json.loads(base64.b64decode(_GOOGLE_OAUTH_CLIENT_BASE64))

    # ======================================== #

    # AdSense
    ADSENSE_ACCOUNT = load_env("ADSENSE_ACCOUNT")
    AD_SLOT_SIDEBAR = load_env("AD_SLOT_SIDEBAR")

    # ======================================== #

    # Redis
    REDIS_HOST = load_env("REDIS_HOST") or "localhost"
    REDIS_PORT = load_env("REDIS_PORT") or 6379
    REDIS_USERNAME = load_env("REDIS_USERNAME") or "default"
    REDIS_PASSWORD = load_env("REDIS_PASSWORD") or ""

    # ======================================== #

    # Flask-Caching
    CACHE_TYPE = load_env("CACHE_TYPE") or "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = load_env("CACHE_DEFAULT_TIMEOUT") or 300
    CACHE_REDIS_URL = (
        f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    )

    # ======================================== #

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = sqlalchemy.URL.create(
        drivername="postgresql+psycopg",
        username=load_env("DB_USER"),
        password=load_env("DB_PASSWORD"),
        host=load_env("DB_HOST") or "localhost",
        port=load_env("DB_PORT") or 5432,  # type: ignore
        database=load_env("DB_NAME"),
    )


class DevConfig(Config):
    HOST = load_env("HOST")
    PORT = load_env("PORT")
    DEBUG = True
    TESTING = True


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
