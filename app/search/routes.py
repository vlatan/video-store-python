import time
from werkzeug.wrappers.response import Response

from flask import (
    render_template,
    request,
    redirect,
    current_app,
    g,
    url_for,
    Blueprint,
    session,
)

from app.models import Post
from app.helpers import query_index_all
from app.search.forms import SearchForm


bp = Blueprint("search", __name__)


@bp.before_app_request
def before_request():
    # before the request make this search form available application wide
    # stored in the global flask variable g
    # the form will send GET request and it's not protected by a CSRF token
    g.search_form = SearchForm(formdata=request.args, meta={"csrf": False})


@bp.route("/search/")
def search_results() -> Response | str | list:
    """Route to return the search results."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    try:  # get page number in URL query params
        page = int(str(request.args.get("page")))
    except ValueError:
        page = 1

    # return JSON response for scroll content if ids and total in session
    ids, total = session.get("ids"), session.get("total")
    if page > 1 and ids and total:
        # if no more search results to serve on scroll
        if total <= (start := (page - 1) * per_page):
            return []
        # get posts for this this page
        posts = Post.get_posts_by_id(ids[start : start + per_page])
        time.sleep(0.4)
        return posts

    # note the time now
    start_time = time.perf_counter()

    # validate the form from which the request is comming
    if not g.search_form.validate():
        return redirect(url_for("main.home"))

    # get the search phrase sent via the search form
    phrase = g.search_form.q.data

    # get the search results
    ids = query_index_all(phrase)
    # save ids and the total number of posts in session
    session["ids"], session["total"] = ids, len(ids)

    # get the first page results
    posts = Post.get_posts_by_id(ids[:per_page])

    # calculate the time it took to get the search results
    time_took = time.perf_counter() - start_time
    # render the template
    return render_template(
        "search.html",
        posts=posts,
        total=session["total"],
        time_took=f"{time_took:.2f}",
        title="Search",
    )
