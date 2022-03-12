import os
import time
from flask import render_template, request, current_app, abort
from flask import Blueprint, jsonify, make_response
from flask_login import current_user
from app.models import Playlist, Post, Page

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


@main.route('/sitemap.xml')
def sitemap_index():
    per_page = current_app.config['POSTS_PER_PAGE'] * 2
    posts = Post.get_sitemap(per_page)
    sources = Playlist.get_sitemap(per_page)
    pages = Page.get_sitemap(per_page)
    return render_template('sitemap_index.xml', posts=posts,
                           sources=sources, pages=pages)


@main.route('/<string:what>-sitemap-<int:page>.xml')
def sitemap_page(what, page):
    per_page = current_app.config['POSTS_PER_PAGE'] * 2
    if what == 'post':
        posts, tp = Post.get_sitemap(per_page), 'posts'
    elif what == 'page':
        posts, tp = Page.get_sitemap(per_page), 'pages'
    elif what == 'source':
        posts, tp = Playlist.get_sitemap(per_page), 'sources'

    if not (posts := posts.get(page)):
        abort(404)

    return render_template('sitemap_page.xml', posts=posts, type=tp)
