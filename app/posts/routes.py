from flask import render_template, url_for, flash
from flask import redirect, Blueprint, current_app, make_response
from flask_login import current_user, login_required
from app import db
from app.helpers import admin_required
from app.models import Post, Playlist
from app.posts.forms import PostForm, PlaylistForm
from app.posts.helpers import convertDuration, revalidate_video
from datetime import datetime, timedelta

posts = Blueprint('posts', __name__)


@posts.route('/post/<int:post_id>/')
def post(post_id):
    post = Post.query.get_or_404(post_id)

    # revalidate video every third day from the last visit
    if post.last_checked + timedelta(days=3) < datetime.utcnow():
        revalidate_video(post)
        # update last checked
        post.last_checked = datetime.utcnow()
        db.session.commit()

    # get standard size thumb, if doesn't exist get high size
    thumb = post.thumbnails.get('standard', post.thumbnails.get('high'))
    # create video duration object
    duration = convertDuration(post.duration)

    return render_template('post.html', post=post, thumb=thumb['url'],
                           duration=duration.human, likes=post.likes.count())


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
        post = Post(**form.content.data, author=current_user)
        # number of related posts to fetch
        per_page = current_app.config['NUM_RELATED_POSTS']
        # search for related videos using the post title
        if (related_posts := Post.search(post.title, 1, per_page)[0].all()):
            post.related_posts = related_posts

        # add post to database
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
        playlist = Playlist(**form.content.data, author=current_user)

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


@posts.route('/post/<int:post_id>/<action>', methods=['POST'])
@login_required
def perform_action(post_id, action):
    post = Post.query.get_or_404(post_id)
    if action == 'like':
        current_user.cast(post, 'like')
        db.session.commit()
        return make_response('Success', 200)
    elif action == 'unlike':
        current_user.uncast(post, 'like')
        db.session.commit()
        return make_response('Success', 200)
    elif action == 'delete' and current_user.is_admin:
        db.session.delete(post)
        db.session.commit()
        flash('The video has been deleted', 'success')
        return redirect(url_for('main.home'))
