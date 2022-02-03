import os
import requests
from flask import render_template, url_for, flash
from flask import redirect, Blueprint, session
from flask_login import current_user, login_required
from app import db

users = Blueprint('users', __name__)


@users.route('/liked')
@login_required
def liked():
    total = len(posts := [like.post for like in current_user.liked])
    return render_template('content.html', posts=posts,
                           total=total, title='Liked')


@users.route('/favorites')
@login_required
def favorites():
    total = len(posts := [fave.post for fave in current_user.faved])
    return render_template('content.html', posts=posts,
                           total=total, title='Favorites')


@users.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    image_name = f'{current_user.id}.jpg'
    image_name = os.path.join('app/static/user_images/', image_name)
    if os.path.exists(image_name):
        os.remove(image_name)

    if current_user.google_id:
        # revoke Doxder app from user's Google account
        # https://tinyurl.com/ymadyw2k
        requests.post('https://oauth2.googleapis.com/revoke',
                      params={'token': session['revoke_token']},
                      headers={'content-type': 'application/x-www-form-urlencoded'})

    db.session.delete(current_user)
    db.session.commit()
    flash('Your account has been deleted', 'success')
    return redirect(url_for('main.home'))
