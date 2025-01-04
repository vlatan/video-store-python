import time
from werkzeug.wrappers.response import Response

from flask import (
    Blueprint,
    current_app,
    request,
    render_template,
    abort,
    make_response,
)

from app import db
from app.models import Category


bp = Blueprint("categories", __name__)


@bp.route("/category/<string:slug>/")
def category(slug: str) -> Response | list | str:
    """Return posts in a category."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    try:  # get page number from URL query params
        page = int(str(request.args.get("page")))
    except ValueError:
        page = 1

    category = db.one_or_404(db.select(Category).filter_by(slug=slug))
    posts = category.get_posts(page=page, per_page=per_page)

    # return JSON response for scroll content
    if page > 1:
        time.sleep(0.4)
        return posts or make_response([], 404)

    if not posts:
        abort(404)

    return render_template("category.html", posts=posts, category=category)
