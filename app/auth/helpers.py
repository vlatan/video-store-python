import os
from app import db
from app.helpers import save_image
from app.models import User
from flask import flash, redirect, request


def failed_login():
    flash('Sorry, there was a problem signing in to your account.', 'info')
    return redirect(request.referrer)


def get_user_ready(user_info):
    if (facebook_id := user_info.get('facebook_id')):
        user = User.query.filter_by(facebook_id=facebook_id).first()
    else:
        user = User.query.filter_by(google_id=user_info['google_id']).first()

    save_local_picture = False
    # if this user does not exist, create it
    if not user:
        user = User(**user_info)
        db.session.add(user)
        db.session.commit()
        if user.picture:
            save_local_picture = True
    # otherwise update mutable info for this user if changed
    else:
        if user.email != user_info['email']:
            user.email = user_info['email']
            db.session.commit()
        if user.name != user_info['name']:
            user.name = user_info['name']
            db.session.commit()
        if user.picture != user_info['picture']:
            user.picture = user_info['picture']
            db.session.commit()
            save_local_picture = True

    if save_local_picture:
        file_name = f'{user.id}.jpg'
        file_path = os.path.join('app/static/user_images/', file_name)
        if save_image(user.picture, file_path):
            user.local_picture = file_name
            db.session.commit()

    return user
