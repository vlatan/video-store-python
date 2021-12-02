import json
from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint, current_app)
from flask_login import current_user, login_required
from doxapp import db
from doxapp.models import Post, Chanel
from doxapp.posts.forms import PostForm
from functools import wraps

posts = Blueprint('posts', __name__)


def admin_required(func):
    @wraps(func)
    def only_admin(*args, **kwargs):
        admin_email = current_app.config['ADMIN_EMAIL']
        if current_user.email != admin_email:
            flash('You need to be admin to access that page!', 'info')
            return redirect(url_for('main.home'))
        return func(*args, **kwargs)
    return only_admin


@posts.route('/post/new/', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        post = Post(**form.content.data, post_author=current_user)

        # check if this video belongs to one of our preselected chanels
        chanel_id = form.content.data['chanel_id']
        chanel = Chanel.query.filter_by(chanel_id=chanel_id).first()
        if chanel:
            # if so add the relationship
            post.chanel = chanel

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
