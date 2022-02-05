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
    return render_template('content.html', posts=posts, user_likes=True,
                           total=total, title='Liked')


@users.route('/favorites')
@login_required
def favorites():
    total = len(posts := [fave.post for fave in current_user.faved])
    return render_template('content.html', posts=posts, user_faves=True,
                           total=total, title='Favorites')


@users.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    image_name = f'{current_user.id}.jpg'
    image_name = os.path.join('app/static/user_images/', image_name)
    if os.path.exists(image_name):
        os.remove(image_name)

    # revoke Doxder app from user's Google/Facebook account
    revoke_token = session['revoke_token']
    if current_user.google_id:
        # https://tinyurl.com/ymadyw2k
        requests.post('https://oauth2.googleapis.com/revoke',
                      params={'token': revoke_token},
                      headers={'content-type': 'application/x-www-form-urlencoded'})
    elif (facebook_id := current_user.facebook_id):
        # https://tinyurl.com/bdd23hnt
        requests.delete(f'https://graph.facebook.com/v12.0/{facebook_id}/permissions',
                        data={'access_token': revoke_token})

    db.session.delete(current_user)
    db.session.commit()
    flash('Your account has been deleted', 'success')
    return redirect(url_for('main.home'))
