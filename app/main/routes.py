import os
import time
import pathlib
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from flask_login import current_user
from flask import (
    render_template,
    request,
    current_app,
    url_for,
    Blueprint,
    send_from_directory,
    redirect,
)

from app.models import Post
from app.auth.helpers import get_avatar_abs_path, download_avatar


bp = Blueprint("main", __name__)


@bp.before_app_request
def redirect_www():
    """Redirect www requests to non-www."""
    urlparts = urlparse(request.url)
    if not (netloc := urlparts.netloc).startswith("www."):
        return

    urlparts = urlparts._replace(netloc=netloc.replace("www.", ""))
    return redirect(urlunparse(urlparts), code=301)


@bp.app_template_filter("autoversion")
def autoversion_file(filename):
    """Autoversion css/js files based on mtime."""
    fullpath = os.path.join("app/", filename[1:])
    try:
        timestamp = round(os.path.getmtime(fullpath))
    except OSError:
        return filename
    return f"{filename}?v={timestamp}"


@bp.app_template_filter()
def format_datetime(value):
    """Datetime formater to use in templates."""
    return value.strftime("%Y-%m-%d %H:%M")


def avatar(user):
    """
    Check if the user has localy saved avatar.
    If so serve it, otherwise attempt so save the avatar locally.
    If not able to save the avatar serve default avatar.
    """
    # get absolute path to the user avatar
    avatar_path = get_avatar_abs_path(user)
    # default avatar path
    avatar = pathlib.Path("images") / "default_avatar.jpg"

    # if user avatar image exists localy
    if pathlib.Path.is_file(avatar_path):
        # user avatar path within the static folder
        avatar = pathlib.Path("images") / "avatars" / f"{user.analytics_id}.jpg"
        # return user avatar url
        return url_for("static", filename=avatar)

    # if this is the admin dashboard page
    if request.referrer == url_for("admin.dashboard", _external=True):
        # get redis client
        redis_client = current_app.config["REDIS_CLIENT"]
        # construct unique user redis key
        redis_key = f"user_{user.id}_download_avatar"

        # if downloading the users' avatar was NOT attempted in the previous day
        if not redis_client.get(redis_key):
            # try to download the user avatar locally
            download_avatar(user)
            # record in Redis that the this user's avatar
            # has been attempted to be downloaded
            WEEK_IN_SECONDS = 7 * 24 * 60 * 60
            redis_client.setex(redis_key, time=WEEK_IN_SECONDS, value="OK")

            # check again if user avatar image exists localy
            if pathlib.Path.is_file(avatar_path):
                # user avatar path within the static folder
                avatar = pathlib.Path("images") / "avatars" / f"{user.analytics_id}.jpg"

    # return user avatar url
    return url_for("static", filename=avatar)


@bp.app_context_processor
def template_vars():
    """Make variables available in templates."""
    return dict(
        now=datetime.utcnow(),
        app_name=current_app.config["APP_NAME"],
        avatar=avatar,
    )


@bp.route("/")
def home() -> list | str:
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
        return posts

    # render HTML template for the first view
    return render_template("home.html", posts=posts)


@bp.route("/<path:filename>")
def favicons(filename):
    """Serve favicon icons as if from root."""
    return send_from_directory("static/favicons/", filename)
