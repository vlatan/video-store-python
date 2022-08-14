import os.path
import time
import hashlib
import requests
from datetime import datetime
from flask import render_template, request, current_app, url_for
from flask import Blueprint, jsonify, make_response, send_from_directory
from flask_login import current_user
from app.models import Post
from app import db

main = Blueprint("main", __name__)


@main.app_template_filter("autoversion")
def autoversion_file(filename):
    """Autoversion css/js files based on mtime."""
    fullpath = os.path.join("app/", filename[1:])
    try:
        timestamp = round(os.path.getmtime(fullpath))
    except OSError:
        return filename
    return f"{filename}?v={timestamp}"


@main.app_template_filter()
def format_datetime(value):
    """Datetime formater to use in templates."""
    return value.strftime("%Y-%m-%d %H:%M")


def generate_hash(user):
    """Generate user's hash id."""
    google_id, fb_id = user.google_id, user.facebook_id
    open_id = google_id if google_id else fb_id
    value = str(user.id) + str(open_id)
    return hashlib.md5(value.encode()).hexdigest()


def hash_id(user):
    """Get user google analytics id."""
    if not user.analytics_id:
        user.analytics_id = generate_hash(user)
        db.session.commit()
    return user.analytics_id


def save_image(image_url, file_path):
    """Save image to file."""
    response = requests.get(image_url)
    if response.ok:
        with open(file_path, "wb") as file:
            file.write(response.content)
            return True
    return False


def avatar(user):
    """
    Check if user has localy saved avatar.
    If so serve it, if not save to file if possible and serve it.
    Otherwise serve default avatar.
    """
    # absolute path to the static folder
    static_folder = os.path.join(current_app.root_path, "static")
    # avatar path relative to the static folder
    rel_avatar = f"images/avatars/{hash_id(user)}.jpg"
    # absolute path to the user avatar
    abs_avatar = os.path.join(static_folder, rel_avatar)
    # if avatar image exists or it is created just now
    if os.path.isfile(abs_avatar) or save_image(user.picture, abs_avatar):
        # return avatar url
        return url_for("static", filename=rel_avatar)
    # return default avatar
    return url_for("static", filename="images/avatars/default.jpg")


@main.app_context_processor
def template_vars():
    """Make variables available in templates."""
    return dict(
        now=datetime.utcnow(),
        app_name=current_app.config["APP_NAME"],
        analytics_id=hash_id,
        avatar=avatar,
    )


@main.route("/", methods=["GET", "POST"])
def home():
    """Route to return the posts."""
    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get("page") if frontend_data else 1

    if current_user.is_authenticated and current_user.is_admin:
        if request.args.get("order_by") == "likes":
            posts = Post.get_posts_by_likes(page, per_page)
        elif request.args.get("short_desc") == "no":
            date = Post.upload_date.desc()
            query = Post.query.filter_by(short_description=None).order_by(date)
            posts = query.paginate(page, per_page, False).items
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

    if request.method == "POST":
        time.sleep(0.4)
        return make_response(jsonify(posts), 200)

    # render template on the first view (GET method)
    return render_template("home.html", posts=posts)


@main.route("/<path:filename>")
def favicons(filename):
    """Serve favicon icons as if from root."""
    return send_from_directory("static/favicons/", filename)
