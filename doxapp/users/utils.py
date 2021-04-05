import os
import secrets
from PIL import Image
from flask import current_app, session, url_for
from flask_login import login_user
from doxapp import db
from doxapp.models import User


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
        username = user_info.get('given_name')
        picture = user_info.get('picture')

        if not username:
            username = 'Guest'
        session['username'] = username

        if not picture:
            picture = url_for('static', filename='profile_pics/default.jpg')
        session['picture'] = picture

        # search for this user in the database by openid
        user = User.query.filter_by(openid=openid).first()
        # if there isn't one create the user
        if not user:
            user = User(openid=openid, email=email)
            db.session.add(user)
            db.session.commit()

        # begin user session by logging the user in
        login_user(user, remember=True)
