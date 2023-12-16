import hashlib
import os.path
import requests
from datetime import timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from flask_login import login_user
from flask import flash, redirect, request, current_app

from app import db
from app.models import User


def finalize_google_login(credentials):
    """Verify token, get user info, log user in."""

    # if credentials is string it comes from OneTap and is in fact an ID token
    if isinstance(credentials, str):
        # verify the integrity of the ID token and get the user info
        user_info = verify_google_token(credentials)
    else:
        # verify the integrity of the ID token and get the user info
        user_info = verify_google_token(credentials.id_token)
        # store refresh token
        user_info["token"] = credentials.token

    # get user ready (create or update their info)
    user = get_user_ready(user_info)
    # begin user session by logging the user in
    login_user(user, remember=True, duration=timedelta(days=30))


def finalize_fb_login(user_info):
    """Get user ready, log user in."""
    # get user ready (create or update their info)
    user = get_user_ready(user_info)
    # begin user session by logging the user in
    login_user(user, remember=True, duration=timedelta(days=30))


def verify_google_token(token):
    """
    Verify the integrity of the Google's ID token and return the user info
    https://tinyurl.com/z2b5xr25, https://tinyurl.com/3dwm6pxe
    """

    CLIENT_ID = current_app.config["GOOGLE_CLIENT_ID"]
    data = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
    # return user info
    return {
        "google_id": data["sub"],
        "email": data.get("email"),
        "name": data.get("given_name", "Guest"),
        "picture": data.get("picture"),
    }


def get_user_ready(user_info):
    """
    Create new user or update the existing one if needed.
    Commit the changes, return the user object.
    """

    if facebook_id := user_info.get("facebook_id"):
        user = User.query.filter_by(facebook_id=facebook_id).first()
    else:
        user = User.query.filter_by(google_id=user_info["google_id"]).first()

    # if this user does not exist, create it
    if not user:
        user = User(**user_info)
        user.analytics_id = generate_hash(user)
        db.session.add(user)
        db.session.commit()
        save_avatar(user)
        return user

    # otherwise update mutable info for this user if changed
    if user.token != user_info["token"]:
        user.token = user_info["token"]
    if user.email != user_info["email"]:
        user.email = user_info["email"]
    if user.name != user_info["name"]:
        user.name = user_info["name"]
    if user.picture != user_info["picture"]:
        user.picture = user_info["picture"]
        save_avatar(user)

    db.session.commit()
    return user


def generate_hash(user):
    """Generate user's hash id."""
    google_id, fb_id = user.google_id, user.facebook_id
    open_id = google_id if google_id else fb_id
    value = str(user.id) + str(open_id)
    return hashlib.md5(value.encode()).hexdigest()


def save_avatar(user):
    """Save avatar to file."""
    response = requests.get(user.picture)
    if response.ok:
        avatar_path = get_avatar_abs_path(user)
        with open(avatar_path, "wb") as file:
            file.write(response.content)


def get_avatar_abs_path(user):
    """Get the local avatar absolute path."""
    root = current_app.root_path
    return os.path.join(root, "static", "images", "avatars", f"{user.analytics_id}.jpg")


def failed_login():
    """Generate flash message and return the referrer."""
    flash("Sorry, there was a problem signing in to your account.", "info")
    return redirect(request.referrer)
