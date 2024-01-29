import os
import time
import pathlib
from redis import Redis
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from werkzeug.wrappers.response import Response

from flask_login import current_user
from flask import (
    render_template,
    request,
    current_app,
    Blueprint,
    make_response,
    send_from_directory,
    redirect,
)

from app import cache
from app.models import User, Post, Category
from app.auth.helpers import get_avatar_abs_path, download_avatar


bp = Blueprint("main", __name__)


FAVICONS = [
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "apple-touch-icon.png",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon.ico",
    "site.webmanifest",
]


def favicons() -> Response:
    """Serve favicon icons as if from root."""
    return send_from_directory("static/favicons/", request.path[1:])


# add routes only for the favicons in the root
for favicon in FAVICONS:
    bp.add_url_rule(rule=f"/{favicon}", view_func=favicons)


@bp.before_app_request
def redirect_www() -> Response | None:
    """Redirect www requests to non-www."""
    urlparts = urlparse(request.url)
    if not (netloc := urlparts.netloc).startswith("www."):
        return

    urlparts = urlparts._replace(netloc=netloc.replace("www.", ""))
    return redirect(urlunparse(urlparts), code=301)


@bp.app_template_filter("autoversion")
def autoversion_file(filename: str) -> str:
    """Autoversion files based on mtime."""

    # filename without the first forward slash
    fn = filename[1:]

    # path to the file on disc
    path = (
        os.path.join("app/static/favicons", fn)
        if fn in FAVICONS
        else os.path.join("app/", fn)
    )

    # try to take e timestamp
    try:
        timestamp = round(os.path.getmtime(path))
    except OSError:
        return filename

    return f"{filename}?v={timestamp}"


@bp.app_template_filter()
def format_datetime(value: datetime) -> str:
    """Datetime formater to use in templates."""
    return value.strftime("%Y-%m-%d %H:%M")


def avatar(user: User, redis_client: Redis | None = None) -> pathlib.Path:
    """
    Check if the user has localy saved avatar.
    If so return its relative path to the "static" folder.
    Otherwise attempt so save the avatar locally.
    If not able to save the avatar serve default avatar relative path.

    Parameters:
    user (User): User object.
    redis_client (Redis): Redis client object if any.

    Returns:
    pathlib.Path: Path object relative to the "static" folder.
    """

    # construct absolute path to the user avatar
    avatar_absoulte_path = get_avatar_abs_path(user)

    # user avatar path within the static folder
    user_avatar = pathlib.Path("images") / "avatars" / f"{user.analytics_id}.jpg"

    # if user avatar image exists localy return user avatar
    if pathlib.Path.is_file(avatar_absoulte_path):
        return user_avatar

    # default avatar path within the static folder
    default_avatar = pathlib.Path("images") / "avatars" / "default_avatar.jpg"

    # get redis client and construct redis key
    redis_client = redis_client or current_app.config["REDIS_CLIENT"]
    redis_key = f"{user.id}:url:{user.picture}"

    # if avatar url in redis then it's not downloadable, serve default avatar
    if redis_client.get(redis_key) == "false".encode():
        return default_avatar

    # try to download user avatar and serve it
    if download_avatar(user):
        return user_avatar

    # if unable to download avatar, cache that state for one week for that URL
    WEEK_IN_SECONDS = 7 * 24 * 60 * 60
    redis_client.setex(redis_key, time=WEEK_IN_SECONDS, value="false")
    return default_avatar


@cache.cached(timeout=86400, key_prefix="all_categories")
def get_categories():
    categories = Category.query.order_by(Category.name).all()
    return [cat for cat in categories if cat.posts.first()]


@bp.app_context_processor
def template_vars():
    """Make variables available in templates."""
    return dict(
        now=datetime.utcnow(),
        avatar=avatar,
        categories=get_categories,
    )


@bp.route("/")
def home() -> Response | list | str:
    """Route to return the posts."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    try:  # get page number in URL query params
        page = int(str(request.args.get("page")))
    except ValueError:
        page = 1

    if current_user.is_authenticated and current_user.is_admin:
        if request.args.get("order_by") == "likes":
            posts = Post.get_posts_by_likes(page, per_page)
        elif request.args.get("short_desc") == "no":
            date = Post.upload_date.desc()
            query = Post.query.filter_by(short_description=None).order_by(date)
            posts = query.paginate(page=page, per_page=per_page, error_out=False).items
            posts = [post.serialize for post in posts]
        else:
            uncached_posts = Post.get_posts.uncached
            posts = uncached_posts(Post, page, per_page)
    else:
        posts = (
            Post.get_posts_by_likes(page, per_page)
            if request.args.get("order_by") == "likes"
            else Post.get_posts(page, per_page)
        )

    # return JSON response for scroll content
    if page > 1:
        time.sleep(0.4)
        return posts or make_response([], 404)

    # render HTML template for the first view
    return render_template("home.html", posts=posts)
