import os
import json
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
    # app
    APP_NAME = load_env("APP_NAME")
    APP_DESCRIPTION = load_env("APP_DESCRIPTION")
    DOMAIN = load_env("DOMAIN")
    SECRET_KEY = load_env("SECRET_KEY")
    GTAG_ID = load_env("GTAG_ID")
    CRON_HOUR = load_env("CRON_HOUR") or 5
    SEND_FILE_MAX_AGE_DEFAULT = load_env("SEND_FILE_MAX_AGE_DEFAULT") or 315360000

    # Redis
    REDIS_HOST = load_env("REDIS_HOST") or "localhost"
    REDIS_PORT = load_env("REDIS_PORT") or 6379
    REDIS_USERNAME = load_env("REDIS_USERNAME") or "default"
    REDIS_PASSWORD = load_env("REDIS_PASSWORD") or ""

    # Flask-Caching
    CACHE_TYPE = load_env("CACHE_TYPE") or "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = load_env("CACHE_DEFAULT_TIMEOUT") or 300
    CACHE_REDIS_URL = (
        f"redis://{REDIS_USERNAME}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}"
    )

    # Admin Google openid
    ADMIN_OPENID = str(load_env("ADMIN_OPENID"))

    # Database
    SQLALCHEMY_DATABASE_URI = sqlalchemy.URL.create(
        "postgresql+psycopg",
        username=load_env("DB_USER"),
        password=load_env("DB_PASSWORD"),
        host=load_env("DB_HOST"),
        port=load_env("DB_PORT") or 5432,  # type: ignore
        database=load_env("DB_NAME"),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Other
    POSTS_PER_PAGE = load_env("POSTS_PER_PAGE") or 24
    NUM_RELATED_POSTS = load_env("NUM_RELATED_POSTS") or 5

    # Google Gemini API key to generate summaries and categories for the videos
    GEMINI_API_KEY = load_env("GEMINI_API_KEY")

    # Facebook authentication
    FB_CLIENT_ID = str(load_env("FB_CLIENT_ID"))
    FB_CLIENT_SECRET = load_env("FB_CLIENT_SECRET")
    FB_GRAPH_ENDPOINT = "https://graph.facebook.com/v12.0"
    FB_DIALOG_ENDPOINT = "https://www.facebook.com/v12.0/dialog/oauth"
    FB_ACCESS_TOKEN_ENDPOINT = os.path.join(FB_GRAPH_ENDPOINT, "oauth", "access_token")
    FB_INSPECT_TOKEN_ENDPOINT = "https://graph.facebook.com/debug_token"

    # Google/Youtube authentication
    YOUTUBE_API_KEY = load_env("YOUTUBE_API_KEY")
    GOOGLE_PROJECT_ID = load_env("GOOGLE_PROJECT_ID")
    GOOGLE_CLIENT_ID = load_env("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = load_env("GOOGLE_CLIENT_SECRET")
    GOOGLE_SCOPES = load_env("GOOGLE_SCOPES")
    GOOGLE_REDIRECT_URIS = load_env("GOOGLE_REDIRECT_URIS")
    GOOGLE_JS_ORIGINS = load_env("GOOGLE_JAVASCRIPT_ORIGINS")
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
    HOST = load_env("HOST")
    PORT = load_env("PORT")
    DEBUG = True
    TESTING = True


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
