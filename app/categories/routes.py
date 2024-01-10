import time

from flask import Blueprint, current_app, request, render_template

from app import db, cache
from app.models import Category


bp = Blueprint("categories", __name__)


@bp.route("/category/<string:slug>/")
def category(slug: str) -> list | str:
    """Return posts in a category."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    try:  # get page number in URL query params
        page = int(str(request.args.get("page")))
    except ValueError:
        page = 1

    category = db.one_or_404(db.select(Category).filter_by(slug=slug))

    posts = category.posts.paginate(page=page, per_page=per_page, error_out=False)
    posts = [post.serialize for post in posts.items]

    # return JSON response for scroll content
    if page > 1:
        time.sleep(0.4)
        return posts

    return render_template("category.html", posts=posts, category=category)
