import time
from flask import render_template, url_for, flash
from flask import redirect, Blueprint, current_app, request, jsonify, make_response
from flask_login import current_user
from app import db
from app.models import Post, Playlist
from app.helpers import admin_required
from app.lists.forms import PlaylistForm

lists = Blueprint('lists', __name__)


@lists.route('/source/new', methods=['GET', 'POST'])
@admin_required
def new_playlist():
    form = PlaylistForm()
    # the form will not validate if the channel is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        playlist = Playlist(**form.content.data, author=current_user)

        # add to db
        db.session.add(playlist)
        db.session.commit()

        flash('Playlist has been added to the database!', 'success')
        return redirect(url_for('lists.playlists'))

    return render_template('form.html', title='Suggest YouTube Playlist',
                           form=form, legend='Playlist')


@lists.route('/source/<string:playlist_id>/', methods=['GET', 'POST'])
def playlist_videos(playlist_id):
    """ Route to return all videos in a playlist """

    # check if playlist exists
    playlist = Playlist.query.filter_by(playlist_id=playlist_id).first_or_404()

    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1

    posts = Post.get_playlist_posts(playlist_id, page, per_page)

    if request.method == 'POST':
        time.sleep(0.4)
        return make_response(jsonify(posts), 200)

    return render_template('source.html', posts=posts, title=playlist.title,
                           playlist_id=playlist_id)


@lists.route('/source/other/', methods=['GET', 'POST'])
def orphan_videos():
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1
    # get orpahn posts
    posts = Post.get_orphans(page, per_page)

    if request.method == 'POST':
        time.sleep(0.4)
        return make_response(jsonify(posts), 200)

    return render_template('source.html', posts=posts, title='Other Uploads')


@lists.route('/sources/')
def playlists():
    """ Route to return the channels """
    # Query the Playlist table
    playlists = Playlist.query.order_by(Playlist.id.desc())
    return render_template('sources.html', posts=playlists, title='Sources')
