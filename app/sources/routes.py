import time
from werkzeug.wrappers.response import Response

from flask_login import current_user
from flask import (
    redirect,
    Blueprint,
    current_app,
    request,
    make_response,
    render_template,
    url_for,
    abort,
    flash,
)

from app import db
from app.models import Post, Playlist
from app.helpers import admin_required
from app.sources.forms import PlaylistForm


bp = Blueprint("sources", __name__)


@bp.route("/source/new", methods=["GET", "POST"])
@admin_required
def new_playlist() -> Response | str:
    form = PlaylistForm()
    # the form will not validate if the channel is already in the database,
    # or if it can't fetch its medatata for various reasons
    if form.validate_on_submit():
        # create object from Model
        # form.content.data is a dict, just unpack to transform into kwargs
        playlist = Playlist(
            **form.processed_content,
            user_id=current_user.id,
            author=current_user,
        )  # type: ignore

        # add to db
        db.session.add(playlist)
        db.session.commit()

        flash("Playlist has been added to the database!", "success")
        return redirect(url_for("sources.playlists"))

    return render_template(
        "form.html", title="Suggest YouTube Playlist", form=form, legend="New Playlist"
    )


@bp.route("/source/<string:playlist_id>/")
def playlist_videos(playlist_id) -> Response | list | str:
    """Route to return all videos in a playlist."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    try:  # get page number in URL query params
        page = int(str(request.args.get("page")))
    except ValueError:
        page = 1

    # check if playlist exists
    playlist = Playlist.query.filter_by(playlist_id=playlist_id).first_or_404()
    posts = Post.get_playlist_posts(playlist_id, page, per_page)

    # return JSON response for scroll content
    if page > 1:
        time.sleep(0.4)
        return posts or make_response([], 404)

    if not posts:
        abort(404)

    return render_template(
        "source.html", posts=posts, title=playlist.title, playlist_id=playlist_id
    )


@bp.route("/source/other/")
def orphan_videos() -> Response | list | str:
    """Route to return all videos that don't belong to a playlist."""

    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]

    try:  # get page number in URL query params
        page = int(str(request.args.get("page")))
    except ValueError:
        page = 1

    # get orpahn posts
    posts = Post.get_orphans(page, per_page)

    # return JSON response for scroll content
    if page > 1:
        time.sleep(0.4)
        return posts or make_response([], 404)

    if not posts:
        abort(404)

    return render_template("source.html", posts=posts, title="Other Uploads")


@bp.route("/sources/")
def playlists():
    """Route to return the channels"""
    # Query the Playlist table
    playlists = Playlist.query.order_by(Playlist.id.desc())
    return render_template("sources.html", posts=playlists, title="Sources")
