import os
import secrets
from PIL import Image
from flask import current_app, url_for, flash, redirect, request
from app import db
from app.models import User


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(
        current_app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def failed_login():
    flash('Sorry, there was a problem signing in to your account.')
    return redirect(request.referrer)


def get_user_ready(openid, user_info):
    email = user_info.get('email')
    username = user_info.get('given_name', 'Guest')
    default_picture = url_for('static', filename='profile_pics/default.jpg')
    picture = user_info.get('picture', default_picture)

    # if this user doesn't exist in our db
    if not (user := User.query.filter_by(openid=openid).first()):
        user = User(openid=openid, email=email,
                    username=username, picture=picture)
        db.session.add(user)
        db.session.commit()
        return user

    # otherwise update mutable info for this user if changed
    if user.email != email:
        user.email = email
        db.session.commit()
    if user.username != username:
        user.username = username
        db.session.commit()
    if user.picture != picture:
        user.picture = picture
        db.session.commit()
    return user
