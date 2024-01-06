from wtforms.validators import ValidationError

from flask_login import current_user, login_required
from flask import render_template, url_for, flash, request
from flask import redirect, Blueprint, current_app, make_response

from app import db
from app.posts.forms import PostForm
from app.helpers import admin_required
from app.models import Post, DeletedPost
from app.cron.handlers import generate_description
from app.posts.helpers import convertDuration, video_banned


bp = Blueprint("posts", __name__)


@bp.route("/video/<string:video_id>/")
def post(video_id):
    # query the post
    post = Post.query.filter_by(video_id=video_id).first_or_404()
    # widest thumb
    thumb = max(post.thumbnails.values(), key=lambda x: x["width"])["url"]
    # get likes text
    num_likes = post.likes.count()
    likes = "1 Like" if num_likes == 1 else f"{num_likes} Likes"
    if not num_likes:
        likes = "Like"
    # how many related posts should we fetch
    PER_PAGE = current_app.config["NUM_RELATED_POSTS"]

    return render_template(
        "post.html",
        post=post,
        thumb=thumb,
        srcset=post.srcset(),
        duration=convertDuration(post.duration).human,
        likes=likes,
        title=post.title,
        related_posts=Post.get_related_posts(post.title, PER_PAGE),
    )


@bp.route("/video/new", methods=["GET", "POST"])
@admin_required
def new_post():
    form = PostForm()
    # the form will not validate if the video is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # if nothing in processed_content
        if not form.processed_content:
            raise ValidationError("Unable to fetch the video data.")
        # check if this video was already deleted
        # and if true remove it from DeletedPost table
        if banned := video_banned(form.processed_content["video_id"]):
            db.session.delete(banned)

        # form.content.data is a dict, just unpack to transform into kwargs
        post = Post(
            **form.processed_content,
            user_id=current_user.id,
            author=current_user,
        )  # type: ignore

        # fetch short description from openAI
        if short_desc := generate_description(post.title):
            post.short_description = short_desc

        # add post to database
        db.session.add(post)
        db.session.commit()

        flash("Your post has been created!", "success")
        return redirect(url_for("posts.post", video_id=post.video_id))

    return render_template(
        "form.html", title="Suggest YouTube Documentary", form=form, legend="New Video"
    )


@bp.route("/video/<string:video_id>/<string:action>", methods=["POST"])
@login_required
def perform_action(video_id, action):
    post = Post.query.filter_by(video_id=video_id).first_or_404()
    if action in ["like", "unlike", "fave", "unfave"]:
        current_user.cast(post, action)
        db.session.commit()
        return make_response("Success", 200)
    elif action == "delete" and current_user.is_admin:
        # add this post to DeletedPost table
        deleted_post = DeletedPost(video_id=post.video_id)
        db.session.add(deleted_post)
        # delete the post
        db.session.delete(post)
        db.session.commit()
        flash("The video has been deleted", "success")
        return redirect(url_for("main.home"))
    elif action == "edit" and current_user.is_admin:
        frontend_data = request.get_json(silent=True)
        if title := frontend_data.get("title"):
            post.title = title
            db.session.commit()
            return make_response("Success", 200)
        elif desc := frontend_data.get("description"):
            post.short_description = desc
            db.session.commit()
            return make_response("Success", 200)
    return make_response("Sorry, can't resolve the request", 400)
