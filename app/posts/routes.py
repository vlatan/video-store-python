from flask import render_template, url_for, flash
from flask import redirect, Blueprint, current_app, make_response
from flask_login import current_user, login_required
from app import db
from app.helpers import admin_required
from app.models import Post
from app.posts.forms import PostForm
from app.posts.helpers import convertDuration

posts = Blueprint('posts', __name__)


@posts.route('/video/<string:video_id>/')
def post(video_id):
    post = Post.query.filter_by(video_id=video_id).first_or_404()

    # get standard size thumb, if doesn't exist get high size
    thumb = post.thumbnails.get('standard', post.thumbnails.get('high'))
    # create video duration object
    duration = convertDuration(post.duration)

    num_likes = post.likes.count()
    likes = '1 Like' if num_likes == 1 else f'{num_likes} Likes'
    if not num_likes:
        likes = 'Like'

    PER_PAGE = current_app.config['NUM_RELATED_POSTS']
    related_posts = Post.get_related_posts(post.title, PER_PAGE)

    return render_template('post.html', post=post, thumb=thumb['url'],
                           duration=duration.human, likes=likes,
                           title=post.title, related_posts=related_posts)


@posts.route('/video/new', methods=['GET', 'POST'])
@admin_required
def new_post():
    form = PostForm()
    # the form will not validate if the video is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # form.content.data is a dict, just unpack to transform into kwargs
        post = Post(**form.processed_content, author=current_user)
        # add post to database
        db.session.add(post)
        db.session.commit()

        flash('Your post has been created!', 'success')
        return redirect(url_for('posts.post', video_id=post.video_id))

    return render_template('form.html', title='Suggest YouTube Documentary',
                           form=form, legend='Documentary')


@posts.route('/video/<string:video_id>/<string:action>', methods=['POST'])
@login_required
def perform_action(video_id, action):
    post = Post.query.filter_by(video_id=video_id).first_or_404()
    if action in ['like', 'unlike', 'fave', 'unfave']:
        current_user.cast(post, action)
        db.session.commit()
        return make_response('Success', 200)
    elif action == 'delete' and current_user.is_admin:
        db.session.delete(post)
        db.session.commit()
        flash('The video has been deleted', 'success')
        return redirect(url_for('main.home'))
    return make_response('Sorry, can\'t resolve the request', 400)
