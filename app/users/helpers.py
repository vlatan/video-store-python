import os
import secrets
from PIL import Image
from flask import current_app
from flask_login import login_user
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


def user_ready(user_info):
    # if user's email verified
    if user_info.get('email_verified'):
        openid = user_info.get('sub')
        email = user_info.get('email')
        username = user_info.get('given_name', 'Guest')
        picture = user_info.get('picture', 'default.jpg')

        # search for this user in the database by openid
        user = User.query.filter_by(openid=openid).first()

        # if user exists
        if user:
            # update mutable info for this user if necessary
            user.email = email
            if username != 'Guest' and user.username != username:
                user.username = username
            if picture != 'default.jpg' and user.picture != picture:
                user.picture = picture
            db.session.commit()
        # if there isn't one create new user
        else:
            user = User(openid=openid, email=email,
                        username=username, picture=picture)
            db.session.add(user)
            db.session.commit()

        # begin user session by logging the user in
        login_user(user, remember=True)
