import os
import time
import pathlib
from datetime import datetime

from flask_login import current_user
from flask import (
    render_template,
    request,
    current_app,
    url_for,
    Response,
    Blueprint,
    jsonify,
    make_response,
    send_from_directory,
)

from app.models import Post
from app.auth.helpers import get_avatar_abs_path, save_avatar


bp = Blueprint("main", __name__)


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
    If so serve it, otherwise serve default avatar.
    """
    # get absolute path to the user avatar
    avatar_path = get_avatar_abs_path(user)

    # # if user avatar image DOES NOT exist localy
    # if not os.path.isfile(avatar_path):
    #     # try to save the image locally
    #     save_avatar(user)

    # default avatar
    avatar = pathlib.Path("images") / "default_avatar.jpg"

    # if user avatar image exists localy
    if os.path.isfile(avatar_path):
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
def home() -> Response | str:
    """Route to return the posts."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    # get page number in URL query args
    page = int(request.args.get("page") or 1)

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

    if page > 1:
        time.sleep(0.4)
        return make_response(jsonify(posts), 200)

    # render template on the first view (GET method)
    return render_template("home.html", posts=posts)


@bp.route("/<path:filename>")
def favicons(filename):
    """Serve favicon icons as if from root."""
    return send_from_directory("static/favicons/", filename)
