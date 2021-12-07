from flask import (render_template, url_for, flash, jsonify, make_response,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from app import db
from app.utils import admin_required
from app.models import Post, Channel
from app.posts.forms import PostForm, ChannelForm
import time

posts = Blueprint('posts', __name__)


@posts.route('/post/<int:post_id>/')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    thumb = post.thumbnails.get('standard', post.thumbnails.get('high'))
    return render_template('post.html', post=post, thumb=thumb['url'])


@posts.route('/post/new/', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    form = PostForm()
    # the form will not validate if the video is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        post = Post(**form.content.data, post_author=current_user)

        # add to db
        db.session.add(post)
        db.session.commit()

        flash('Your post has been created!', 'success')
        return redirect(url_for('main.home'))

    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@posts.route('/channel/new/', methods=['GET', 'POST'])
@login_required
@admin_required
def new_channel():
    form = ChannelForm()
    # the form will not validate if the channel is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        channel = Channel(**form.content.data, channel_author=current_user)

        # check if there are videos alrady posted from this channel
        channel_id = form.content.data['channel_id']
        videos = Post.query.filter_by(channel_id=channel_id).all()
        if videos:
            for video in videos:
                # if so add the relationship
                video.channel = channel

        # add to db
        db.session.add(channel)
        db.session.commit()

        flash('Your channel has been added to the database!', 'success')
        return redirect(url_for('posts.channels'))

    return render_template('add_channel.html', title='New Channel',
                           form=form, legend='New Channel')


@posts.route('/channels')
def channels():
    """ Route to return the channels """

    # Query the Channel table
    channels = Channel.query.order_by(Channel.id.desc())

    return render_template('channels.html', posts=channels, title='Channels')


@posts.route('/post/<int:post_id>/delete/', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted', 'success')
    return redirect(url_for('main.home'))
