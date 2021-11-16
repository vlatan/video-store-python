import os
import hashlib
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from flask import (render_template, url_for, flash, session,
                   redirect, request, Blueprint, current_app)
from flask_login import current_user, logout_user, login_required
from doxapp import db
from doxapp.models import User, Post
from doxapp.users.forms import UpdateAccountForm
from doxapp.users.utils import save_picture, user_ready

users = Blueprint('users', __name__)


@users.route('/oauth/onetap', methods=['POST'])
def onetap():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    csrf_token_body = request.form.get('g_csrf_token')
    csrf_token_cookie = request.cookies.get('g_csrf_token')
    if not (csrf_token_body and csrf_token_body == csrf_token_cookie):
        # log this instead of flashing
        flash('Failed to verify double submit cookie.', 'info')
        return redirect(url_for('main.home'))

    try:
        # verify the integrity of the ID token and get the user info
        token = request.form.get('credential')
        CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
        user_info = id_token.verify_oauth2_token(
            token, grequests.Request(), CLIENT_ID)
    except Exception as e:
        # in production log this error instead of flashing it
        flash(e, 'info')
        return redirect(url_for('main.home'))

    # login user
    user_ready(user_info)
    return redirect(url_for('main.home'))


@users.route('/oauth')
def oauth():
    if current_user.is_authenticated:
        return render_template('close_oauth.html')

    try:
        DISCOVERY_URL = current_app.config['GOOGLE_DISCOVERY_URL']
        PROVIDER = requests.get(DISCOVERY_URL).json()
    # log this error
    except Exception:
        return render_template('close_oauth.html')

    CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
    CLIENT_SECRET = current_app.config['GOOGLE_OAUTH_CLIENT_SECRET']
    SCOPE = current_app.config['GOOGLE_OAUTH_SCOPES']
    REDIRECT_URI = url_for('users.oauth', _external=True)
    AUTH_ENDPOINT = PROVIDER['authorization_endpoint']
    TOKEN_ENDPOINT = PROVIDER['token_endpoint']

    # check if this view has 'code' argument in it
    if 'code' not in request.args:
        # create an anti-forgery unique token
        STATE = hashlib.sha256(os.urandom(1024)).hexdigest()
        # put it in a session
        session['state'] = STATE
        # construct the authorization url
        auth_uri = (f'{AUTH_ENDPOINT}?response_type=code&'
                    f'state={STATE}&client_id={CLIENT_ID}&'
                    f'redirect_uri={REDIRECT_URI}&scope={SCOPE}')
        # request authorization from Google
        return redirect(auth_uri)
    else:
        # check if the anti-forgery unique session token is valid
        if request.args.get('state') != session['state']:
            return render_template('close_oauth.html')
        # get the code Google sent us
        auth_code = request.args.get('code')
        # construct the payload for getting the credentials
        data = {'code': auth_code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'grant_type': 'authorization_code'}
        try:
            # get the credentials from Google
            credentials = requests.post(TOKEN_ENDPOINT, data=data).json()
        except Exception as e:
            flash(e, "info")
            return render_template('close_oauth.html')

        try:
            # verify the integrity of the ID token and return the user info
            token = credentials.get('id_token')
            user_info = id_token.verify_oauth2_token(
                token, grequests.Request(), CLIENT_ID)
        except Exception as e:
            flash(e, 'info')
            return render_template('close_oauth.html')

        # login user
        user_ready(user_info)
        return render_template('close_oauth.html')


@users.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@users.route('/account/', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = current_user.picture
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@users.route('/user/<string:username>')
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)
