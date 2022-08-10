import time
from flask import render_template, request, redirect, current_app, g
from flask import url_for, Blueprint, jsonify, make_response, session
from app.helpers import query_index_all
from app.search.forms import SearchForm
from app.models import Post


search = Blueprint("search", __name__)


@search.before_app_request
def before_request():
    # before the request make this search form available application wide
    # stored in the global flask variable g
    # the form will send GET request and it's not protected by a CSRF token
    g.search_form = SearchForm(formdata=request.args, meta={"csrf": False})


@search.route("/search/", methods=["GET", "POST"])
def search_results():
    """Route to return the search results."""
    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    # if it's the first page
    if request.method == "GET":
        # note the time now
        start_time = time.time()
        # validate the form from which the request is comming
        if not g.search_form.validate():
            return redirect(url_for("main.home"))
        keyword = g.search_form.q.data
        # get the search results
        ids = query_index_all(Post.__searchable__, keyword)
        # save ids and the total number of posts in session
        session["ids"], session["total"] = ids, len(ids)

        # get the first page results
        posts = Post.get_posts_by_id(ids[:per_page])

        # calculate the time it took to get the search results
        time_took = round(time.time() - start_time, 2)
        # render the template
        return render_template(
            "search.html",
            posts=posts,
            total=session["total"],
            time_took=time_took,
            title="Search",
        )

    # load the next page (POST request)
    ids, total = session.get("ids"), session.get("total")
    if (frontend_data := request.get_json()) and ids and total:
        # get the page number
        page = frontend_data.get("page")
        # if there are subsequent posts send content to frontend
        if total > (start := (page - 1) * per_page):
            # get posts from this page
            posts = Post.get_posts_by_id(ids[start : start + per_page])
            time.sleep(0.4)
            return make_response(jsonify(posts), 200)

    # if there are no more pages
    return make_response(jsonify([]), 200)
