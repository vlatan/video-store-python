import os
import time
import datetime
from collections import OrderedDict
from flask import render_template, request, current_app, abort, url_for
from flask import Blueprint, jsonify, make_response, send_from_directory
from flask_login import current_user
from app import cache
from app.models import Playlist, Post, Page

main = Blueprint('main', __name__)


# autoversion css/js files
@main.app_template_filter('autoversion')
def autoversion_filter(filename):
    fullpath = os.path.join('app/', filename[1:])
    try:
        timestamp = round(os.path.getmtime(fullpath))
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
@cache.cached(timeout=86400)
def sitemap_index():
    data = OrderedDict()

    data.update(Post.get_index(order_by='upload_date'))
    data.update(Page.get_index())
    data.update(Playlist.get_index())

    url = url_for('main.sitemap_page', what='misc', page=1, _external=True)
    last_post = Post.query.order_by(Post.upload_date.desc()).first()
    last_source = Playlist.query.order_by(Playlist.id.desc()).first()
    default_date = datetime.datetime.min
    last_post_date = last_post.created_at if last_post else default_date
    last_source_date = last_source.created_at if last_source else default_date
    if not (last_post_date == last_source_date == default_date):
        lastmod = max(last_post_date, last_source_date)
        data[url] = lastmod.strftime('%Y-%m-%d')

    if not data:
        abort(404)

    template = render_template('sitemap_index.xml', data=data)
    response = make_response(template)
    response.headers['content-type'] = 'text/xml; charset=utf-8'
    return response


@main.route('/<string:what>-sitemap-<int:page>.xml')
@cache.cached(timeout=86400)
def sitemap_page(what, page):
    data = OrderedDict()

    if what == 'post':
        data.update(Post.get_sitemap_page(page, order_by='upload_date'))
    elif what == 'page':
        data.update(Page.get_sitemap_page(page))
    elif what == 'playlist':
        data.update(Playlist.get_sitemap_page(page))
    elif what == 'misc':
        home_lastmod = Post.query.order_by(
            Post.upload_date.desc()).first().created_at
        data[url_for('main.home', _external=True)] = home_lastmod

        sources_lastmod = Playlist.query.order_by(
            Playlist.id.desc()).first().created_at
        data[url_for('lists.playlists', _external=True)] = sources_lastmod

    if not data:
        abort(404)

    template = render_template('sitemap_page.xml', data=data)
    response = make_response(template)
    response.headers['content-type'] = 'text/xml; charset=utf-8'
    return response


@main.route('/sitemap.xsl')
@cache.cached(timeout=86400)
def sitemap_style():
    template = render_template('sitemap.xsl')
    response = make_response(template)
    response.headers['content-type'] = 'text/xsl; charset=utf-8'
    return response


@main.route('/<path:name>')
def favicons(name):
    """ Serve favicon icons as if from root """
    return send_from_directory('static/favicons/', name)
