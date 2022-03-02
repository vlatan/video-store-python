from flask import render_template, url_for, flash
from flask import redirect, Blueprint
from flask_login import current_user, login_required
from app import db
from app.models import Playlist
from app.helpers import admin_required
from app.lists.forms import PlaylistForm

lists = Blueprint('lists', __name__)


@lists.route('/source/new', methods=['GET', 'POST'])
@login_required
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
        return redirect(url_for('posts.playlists'))

    return render_template('form.html', title='Suggest YouTube Playlist',
                           form=form, legend='Playlist')


@lists.route('/sources/')
def playlists():
    """ Route to return the channels """
    # Query the Playlist table
    playlists = Playlist.query.order_by(Playlist.id.desc())
    return render_template('playlists.html', posts=playlists, title='Playlists')
