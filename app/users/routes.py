import os
import time
import requests
from datetime import datetime

from flask_login import current_user, login_required
from flask import redirect, Blueprint, current_app, make_response
from flask import render_template, url_for, flash, request, jsonify

from app import db
from app.auth.helpers import get_avatar_abs_path


bp = Blueprint("users", __name__)


@bp.before_app_request
def record_last_visit():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route("/liked/", methods=["GET", "POST"])
@login_required
def liked():
    """Route to return the liked posts."""
    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]
    # if it's POST request this should contain data
    frontend_data = request.get_json(silent=True)
    # if frontend_data get page number, else 1
    page = frontend_data.get("page") if frontend_data else 1

    items = current_user.liked.paginate(
        page=page, per_page=per_page, error_out=False
    ).items
    posts = [item.post for item in items]

    if request.method == "POST":
        # if there are subsequent pages send posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    content_title = "Documentaries you like will show up here."
    if total := current_user.liked.count():
        content_title = "Documentaries You Like:"

    return render_template(
        "library.html",
        posts=posts,
        total=total,
        title="Liked",
        content_title=content_title,
    )


@bp.route("/favorites/", methods=["GET", "POST"])
@login_required
def favorites():
    """Route to return the liked posts"""
    # posts per page
    per_page = current_app.config["POSTS_PER_PAGE"]
    # if it's POST request this should contain data
    frontend_data = request.get_json(silent=True)
    # if frontend_data get page number, else 1
    page = frontend_data.get("page") if frontend_data else 1

    items = current_user.faved.paginate(
        page=page, per_page=per_page, error_out=False
    ).items
    posts = [item.post for item in items]

    if request.method == "POST":
        # if there are subsequent pages send posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    content_title = "Your favorite documentaries will show up here."
    if total := current_user.faved.count():
        content_title = "Your Favorite Documentaries:"

    return render_template(
        "library.html",
        posts=posts,
        total=total,
        title="Favorites",
        content_title=content_title,
    )


@bp.route("/account/delete/", methods=["POST"])
@login_required
def delete_account():
    """Delete users's account."""
    # if user has token try to remove the app from user's Google/Facebook account
    if revoke_token := current_user.token:
        if current_user.google_id:
            # https://tinyurl.com/ymadyw2k
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": revoke_token},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
        elif facebook_id := current_user.facebook_id:
            # https://tinyurl.com/bdd23hnt
            requests.delete(
                f"https://graph.facebook.com/v12.0/{facebook_id}/permissions",
                data={"access_token": revoke_token},
            )

    # save avatar absolute path before deleting user
    avatar_path = get_avatar_abs_path(current_user)
    # remove user
    db.session.delete(current_user)
    db.session.commit()
    # remove local avatar
    os.remove(avatar_path)

    flash("Your account has been deleted", "success")
    return redirect(url_for("main.home"))
