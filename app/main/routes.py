import os
import time
from flask import render_template, request, current_app
from flask import Blueprint, jsonify, make_response, url_for
from app.models import Post

main = Blueprint('main', __name__)


# autoversion css/js files
@main.app_template_filter('autoversion')
def autoversion_filter(filename):
    fullpath = os.path.join('app/', filename[1:])
    try:
        timestamp = os.path.getmtime(fullpath)
    except OSError:
        return filename
    return f'{filename}?v={timestamp}'


@main.route('/', methods=['GET', 'POST'])
def home():
    """ Route to return the posts """
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1

    if request.referrer == url_for('posts.new_post', _external=True):
        # https://flask-caching.readthedocs.io/en/latest/api.html#flask_caching.Cache.memoize
        uncached_posts = Post.get_posts.uncached
        posts = Post.get_posts_by_likes(page, per_page) if request.args.get(
            'order_by') == 'likes' else uncached_posts(Post, page, per_page)
    else:
        posts = Post.get_posts_by_likes(page, per_page) if request.args.get(
            'order_by') == 'likes' else Post.get_posts(page, per_page)

    if request.method == 'POST':
        time.sleep(0.4)
        return make_response(jsonify(posts), 200)

    # render template on the first view (GET method)
    return render_template('content.html', posts=posts,
                           total=per_page + 1)


@main.route('/about')
def about():
    return render_template('about.html', title='About')
