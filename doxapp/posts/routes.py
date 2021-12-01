import json
from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint, current_app)
from flask_login import current_user, login_required
from doxapp import db
from doxapp.models import Post
from doxapp.posts.forms import PostForm
from functools import wraps

posts = Blueprint('posts', __name__)


def admin_required(func):
    @wraps(func)
    def only_admin(*args, **kwargs):
        admin_openid = current_app.config['ADMIN_OPENID']
        if current_user.openid != admin_openid:
            return redirect(url_for('main.home'))
        return func(*args, **kwargs)
    return only_admin


@posts.route('/post/new/', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(provider=form.content.data['provider_name'],
                    video_id=form.content.data['video_id'],
                    chanel_id=form.content.data['chanel_id'],
                    title=form.content.data['title'],
                    thumbnails=form.content.data['thumbnails'],
                    upload_date=form.content.data['upload_date'],
                    post_author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@posts.route('/post/<int:post_id>/')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


@posts.route('/post/<int:post_id>/update/', methods=['GET', 'POST'])
@login_required
@admin_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated', 'success')
        return redirect(url_for('posts.post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


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
