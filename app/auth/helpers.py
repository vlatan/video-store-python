from app import db
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

    # if this user does not exist, create it
    if not user:
        user = User(**user_info)
        db.session.add(user)
        db.session.commit()
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

    return user
