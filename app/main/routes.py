import os
import time
import hashlib
from datetime import datetime
from flask import render_template, request, current_app
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


def generate_analytics_id(user):
    """Generate user google analytics id."""
    google_id, fb_id = user.google_id, user.facebook_id
    open_id = google_id if google_id else fb_id
    value = str(user.id) + str(open_id)
    return hashlib.md5(value.encode()).hexdigest()


def get_analytics_id():
    """Get user google analytics id."""
    if not current_user.is_authenticated:
        return None
    if not current_user.analytics_id:
        current_user.analytics_id = generate_analytics_id(current_user)
        db.session.commit()
    return current_user.analytics_id


@main.app_context_processor
def template_vars():
    """Make variables available in templates."""
    return dict(
        now=datetime.utcnow(),
        app_name=current_app.config["APP_NAME"],
        analytics_id=get_analytics_id(),
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
