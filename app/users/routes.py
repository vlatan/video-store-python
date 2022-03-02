import os
import time
import requests
from flask import render_template, url_for, flash, request, jsonify
from flask import redirect, Blueprint, session, current_app, make_response
from flask_login import current_user, login_required
from app import db

users = Blueprint('users', __name__)


@users.route('/liked/', methods=['GET', 'POST'])
@login_required
def liked():
    """ Route to return the liked posts """
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1

    items = current_user.liked.paginate(page, per_page, False).items
    posts = [item.post for item in items]

    if request.method == 'POST':
        # if there are subsequent pages send posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    total = current_user.liked.count()
    return render_template('library.html', posts=posts,
                           total=total, title='Liked',
                           content_title='Documentaries You Liked:')


@users.route('/favorites/', methods=['GET', 'POST'])
@login_required
def favorites():
    """ Route to return the liked posts """
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1

    items = current_user.faved.paginate(page, per_page, False).items
    posts = [item.post for item in items]

    if request.method == 'POST':
        # if there are subsequent pages send posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    total = current_user.faved.count()
    return render_template('library.html', posts=posts,
                           total=total, title='Favorites',
                           content_title='Your Favorite Documentaries:')


@users.route('/account/delete/', methods=['POST'])
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
