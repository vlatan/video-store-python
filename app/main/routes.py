import os
import time
from datetime import datetime
from flask import render_template, request, current_app
from flask import Blueprint, jsonify, make_response, send_from_directory
from flask_login import current_user
from app import cache
from app.models import Post

main = Blueprint('main', __name__)


@main.app_template_filter('autoversion')
def autoversion_filter(filename):
    """Autoversion css/js files based on mtime."""
    fullpath = os.path.join('app/', filename[1:])
    try:
        timestamp = round(os.path.getmtime(fullpath))
    except OSError:
        return filename
    return f'{filename}?v={timestamp}'


@main.app_context_processor
@cache.cached(timeout=86400)
def template_vars():
    """Make variables available in templates."""
    return dict(now=datetime.utcnow(),
                app_name=current_app.config['APP_NAME'])


@main.route('/', methods=['GET', 'POST'])
def home():
    """Route to return the posts."""
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1

    if current_user.is_authenticated and current_user.is_admin:
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
    return render_template('home.html', posts=posts)


@main.route('/<path:name>')
def favicons(name):
    """ Serve favicon icons as if from root """
    return send_from_directory('static/favicons/', name)
