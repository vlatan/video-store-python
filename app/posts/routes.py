from flask import render_template, url_for, flash
from flask import redirect, abort, Blueprint, current_app
from flask_login import current_user, login_required
from wtforms.validators import ValidationError
from googleapiclient.errors import HttpError
from app import db
from app.helpers import admin_required
from app.models import Post, Playlist
from app.posts.forms import PostForm, PlaylistForm
from app.posts.helpers import validate_video, convertDuration
from googleapiclient.discovery import build
from datetime import datetime, timedelta

posts = Blueprint('posts', __name__)


@posts.route('/post/<int:post_id>/')
def post(post_id):
    post = Post.query.get_or_404(post_id)

    # perform this check every third day from the last visit
    if post.last_checked + timedelta(days=3) < datetime.utcnow():
        # check if the video is still alive on YouTube
        # and still satisfies all the conditions
        API_KEY = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=API_KEY) as youtube:
            try:
                scope = {'id': post.video_id,
                         'part': ['status', 'snippet', 'contentDetails']}
                req = youtube.videos().list(**scope)
                # this will raise IndexError if ['items'] is empty list
                # which means the video does not exist
                res = req.execute()['items'][0]
                # this will raise ValidationError if video's invalid
                validate_video(res)
            # video is not validated or doesn't exist
            except (IndexError, ValidationError):
                db.session.delete(post)
                db.session.commit()
                abort(404)
            except HttpError:
                # we couldn't connect to YT API,
                # so we can't evaluate the video
                pass

        # number of related posts to fetch
        per_page = current_app.config['NUM_RELATED_POSTS']
        # get related posts by searching the index using the title of this post
        related_posts = Post.search(post.title, 1, per_page + 1)[0].all()[1:]
        # if there's change in the related posts
        if post.related_posts != related_posts:
            # update related posts
            post.related_posts = related_posts

        # update last checked
        post.last_checked = datetime.utcnow()
        db.session.commit()

    # get standard size thumb, if doesn't exist get high size
    thumb = post.thumbnails.get('standard', post.thumbnails.get('high'))
    # create video duration object
    duration = convertDuration(post.duration)

    return render_template('post.html', post=post, thumb=thumb['url'], duration=duration.human)


@posts.route('/post/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    form = PostForm()
    # the form will not validate if the video is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        post = Post(**form.content.data, video_poster=current_user)

        # add to db
        db.session.add(post)
        db.session.commit()

        flash('Your post has been created!', 'success')
        return redirect(url_for('main.home'))

    return render_template('form.html', title='Suggest Documentary',
                           form=form, legend='Suggest Documentary')


@posts.route('/playlist/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_playlist():
    form = PlaylistForm()
    # the form will not validate if the channel is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        playlist = Playlist(**form.content.data, playlist_poster=current_user)

        # add to db
        db.session.add(playlist)
        db.session.commit()

        flash('Playlist has been added to the database!', 'success')
        return redirect(url_for('posts.playlists'))

    return render_template('form.html', title='Suggest Playlist',
                           form=form, legend='Suggest YouTube Playlist')


@posts.route('/playlists')
def playlists():
    """ Route to return the channels """
    # Query the Playlist table
    playlists = Playlist.query.order_by(Playlist.id.desc())
    return render_template('playlists.html', posts=playlists, title='Playlists')


@posts.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('The video has been deleted', 'success')
    return redirect(url_for('main.home'))
