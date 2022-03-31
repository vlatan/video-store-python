import time
import datetime
from collections import OrderedDict
from itertools import groupby
from functools import wraps
from flask import render_template, current_app, abort, url_for
from flask import Blueprint, make_response
from app import cache
from app.models import Playlist, Post, Page
from sqlalchemy import func

sitemap = Blueprint('sitemap', __name__)


def serve_as(content_type='text/html', charset='utf-8'):
    """Modify response's content-type header."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            template = func(*args, **kwargs)
            response = make_response(template)
            response.headers['content-type'] = f'{content_type}; charset={charset}'
            return response
        return wrapper
    return decorator


@sitemap.route('/sitemap.xml')
@cache.cached(timeout=86400)
@serve_as(content_type='text/xml')
def sitemap_index():
    """Route to return the sitemap index."""
    data = OrderedDict()
    # posts
    posts = Post.query.order_by(Post.upload_date.desc()).all()
    grouped = groupby(posts, lambda x: x.upload_date.strftime('%Y-%m'))
    for key, group in grouped:
        url = url_for('main.posts_sitemap', date=key, _external=True)
        lastmod = max([obj.updated_at for obj in group])
        data[url] = lastmod.strftime('%Y-%m-%d')

    # pages
    if (latest := Page.query.order_by(Page.updated_at.desc()).first()):
        url = url_for('main.pages_sitemap', _external=True)
        data[url] = latest.created_at.strftime('%Y-%m-%d')

    # sources
    lastmods, per_page = [], current_app.config['POSTS_PER_PAGE']
    for source in Playlist.query:
        posts = Post.get_playlist_posts(source.playlist_id, 1, per_page)
        dates = [post['created_at'] for post in posts]
        lastmods.append(max(dates)) if dates else None
    if lastmods:
        url = url_for('main.sources_sitemap', _external=True)
        data[url] = max(lastmods).strftime('%Y-%m-%d')

    # misc
    last_post = Post.query.order_by(Post.upload_date.desc()).first()
    last_source = Playlist.query.order_by(Playlist.id.desc()).first()
    default_date = datetime.datetime.min
    last_post_date = last_post.created_at if last_post else default_date
    last_source_date = last_source.created_at if last_source else default_date
    if not (last_post_date == last_source_date == default_date):
        url = url_for('main.misc_sitemap', _external=True)
        lastmod = max(last_post_date, last_source_date)
        data[url] = lastmod.strftime('%Y-%m-%d')

    if not data:
        abort(404)

    return render_template('sitemap_index.xml', data=data)


@sitemap.route('/posts-sitemap-<string:date>.xml')
@cache.cached(timeout=86400)
@serve_as(content_type='text/xml')
def posts_sitemap(date):
    """Route to return the posts sitemap."""
    data = OrderedDict()
    posts = Post.query.filter(func.strftime('%Y-%m', Post.upload_date) == date)
    for post in posts:
        url = url_for('posts.post', video_id=post.video_id, _external=True)
        data[url] = post.updated_at.strftime('%Y-%m-%d')

    if not data:
        abort(404)

    return render_template('sitemap_page.xml', data=data)


@sitemap.route('/pages-sitemap.xml')
@cache.cached(timeout=86400)
@serve_as(content_type='text/xml')
def pages_sitemap():
    """Route to return the pages sitemap."""
    data = OrderedDict()
    for page in Page.query:
        url = url_for('pages.page', slug=page.slug, _external=True)
        data[url] = page.updated_at.strftime('%Y-%m-%d')

    if not data:
        abort(404)

    return render_template('sitemap_page.xml', data=data)


@sitemap.route('/sources-sitemap.xml')
@cache.cached(timeout=86400)
@serve_as(content_type='text/xml')
def sources_sitemap():
    """Route to return the sources sitemap."""
    data, per_page = OrderedDict(), current_app.config['POSTS_PER_PAGE']
    for source in Playlist.query:
        url = url_for('lists.playlist_videos',
                      playlist_id=source.playlist_id, _external=True)
        posts = Post.get_playlist_posts(source.playlist_id, 1, per_page)
        dates = [post['created_at'] for post in posts]
        data[url] = max(dates).strftime('%Y-%m-%d')

    if (other_posts := Post.get_orphans(1, per_page)):
        lastmods = [post['created_at'] for post in other_posts]
        url = url_for('lists.orphan_videos', _external=True)
        data[url] = max(lastmods).strftime('%Y-%m-%d')

    if not data:
        abort(404)

    return render_template('sitemap_page.xml', data=data)


@sitemap.route('/misc-sitemap.xml')
@cache.cached(timeout=86400)
@serve_as(content_type='text/xml')
def misc_sitemap():
    """Route to return the miscellaneous sitemap."""
    data, per_page = OrderedDict(), current_app.config['POSTS_PER_PAGE']
    if (posts := Post.get_posts(1, per_page)):
        dates = [post['created_at'] for post in posts]
        home_lastmod = max(dates).strftime('%Y-%m-%d')
        data[url_for('main.home', _external=True)] = home_lastmod

    if (sources_last := Playlist.query.order_by(Playlist.id.desc()).first()):
        sources_lastmod = sources_last.created_at.strftime('%Y-%m-%d')
        data[url_for('lists.playlists', _external=True)] = sources_lastmod

    if not data:
        abort(404)

    return render_template('sitemap_page.xml', data=data)


@sitemap.route('/sitemap.xsl')
@cache.cached(timeout=86400)
@serve_as(content_type='text/xsl')
def sitemap_style():
    return render_template('sitemap.xsl')
