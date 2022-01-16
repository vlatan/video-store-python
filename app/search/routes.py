import time
from flask import render_template, request, redirect, current_app, g
from flask import url_for, Blueprint, jsonify, make_response, session
from app.search.forms import SearchForm
from app.models import Post


search = Blueprint('search', __name__)


@search.before_app_request
def before_request():
    # before the request make this search form available application wide
    # stored in the global flask variable g
    # the form will send GET request and it's not be protected by a CSRF token
    g.search_form = SearchForm(formdata=request.args, meta={'csrf': False})


@search.route('/search', methods=['GET', 'POST'])
def search_results():
    """ Route to return search results using Elasticsearch """
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']

    # if it's the first page
    if request.method == 'GET':
        # validate the form from which the request is comming
        if not g.search_form.validate():
            return redirect(url_for('main.home'))
        keyword = g.search_form.q.data
        # get the search results
        posts, total = Post.search(keyword, 1, per_page)
        # save keyword and the total number of posts in session
        session['keyword'], session['total'] = keyword, total
        # render the template
        return render_template('search.html', posts=posts, total=total)

    keyword, total = session['keyword'], session['total']
    # if we got the frontend data (POST), the keyword and the total number of posts
    if (frontend_data := request.get_json()) and keyword and total:
        # get the page number
        page = frontend_data.get('page')
        posts_so_far = page * per_page
        # if there are subsequent pages send content to frontend
        if total > posts_so_far or posts_so_far - total <= per_page:
            # get the search results
            posts, total = Post.search(keyword, page, per_page)
            # posts as JSON object
            posts = jsonify([post.serialize for post in posts])
            # Simulate delay
            time.sleep(0.4)
            return make_response(posts, 200)

    # if there are no more pages
    return make_response(jsonify([]), 200)
