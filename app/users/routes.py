import os
import hashlib
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as g_requests
from flask import render_template, url_for, flash, session, abort
from flask import redirect, request, Blueprint, current_app
from flask_login import current_user, logout_user, login_required
from app import db
from app.users.forms import UpdateAccountForm
from app.users.helpers import user_ready
import google.oauth2.credentials
import google_auth_oauthlib.flow

users = Blueprint('users', __name__)


@users.route('/oauth/onetap', methods=['POST'])
def onetap():
    if current_user.is_authenticated:
        return redirect(request.referrer)

    fail_message = 'Sorry, there was a problem signing in to your account.'
    csrf_token_cookie = request.cookies.get('g_csrf_token')
    if not csrf_token_cookie:
        # No CSRF token in Cookie.
        abort(400, fail_message)
    csrf_token_body = request.form.get('g_csrf_token')
    if not csrf_token_body:
        # No CSRF token in post body.
        abort(400, fail_message)
        return redirect(request.referrer)
    if csrf_token_cookie != csrf_token_body:
        # Failed to verify double submit cookie.
        abort(400, fail_message)

    try:
        # verify the integrity of the ID token and get the user info
        token = request.form.get('credential')
        CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
        user_info = id_token.verify_oauth2_token(
            token, g_requests.Request(), CLIENT_ID)
        # check if there's user ID, if not it will raise ValueError
        user_id = user_info['sub']
    except ValueError:
        # Invalid token
        abort(400, fail_message)

    # login user
    user_ready(user_info)
    return redirect(request.referrer)


@users.route('/oauth')
def oauth():
    if current_user.is_authenticated:
        return render_template('close_oauth.html')

    CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
    CLIENT_SECRET = current_app.config['GOOGLE_OAUTH_CLIENT_SECRET']
    SCOPE = current_app.config['GOOGLE_OAUTH_SCOPES']
    REDIRECT_URI = url_for('users.oauth', _external=True)
    AUTH_ENDPOINT = current_app.config['GOOGLE_OAUTH_CLIENT_CONFIG']['web']['auth_uri']
    TOKEN_ENDPOINT = current_app.config['GOOGLE_OAUTH_CLIENT_CONFIG']['web']['token_uri']

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
                token, g_requests.Request(), CLIENT_ID)
        except Exception as e:
            flash(e, 'info')
            return render_template('close_oauth.html')

        # login user
        user_ready(user_info)
        return render_template('close_oauth.html')


@users.route('/authorize')
def authorize():
    CLIENT_CONFIG = current_app.config['GOOGLE_OAUTH_CLIENT_CONFIG']
    SCOPES = current_app.config['GOOGLE_OAUTH_SCOPES']
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = url_for('users.oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    # Store the state so the callback can verify the auth server response.
    session['state'] = state

    return redirect(authorization_url)


@users.route('/oauth2callback')
def oauth2callback():
    CLIENT_CONFIG = current_app.config['GOOGLE_OAUTH_CLIENT_CONFIG']
    CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
    SCOPES = current_app.config['GOOGLE_OAUTH_SCOPES']
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('users.oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials

    try:
        # verify the integrity of the ID token and return the user info
        user_info = id_token.verify_oauth2_token(
            credentials.token, g_requests.Request(), CLIENT_ID)
    except Exception as e:
        flash(str(e), 'info')
        return render_template('close_oauth.html')

    # login user
    user_ready(user_info)
    return render_template('close_oauth.html')


@users.route('/logout')
@login_required
def logout():
    logout_user()
    login_needed = [url_for('users.account', _external=True),
                    url_for('posts.new_post', _external=True),
                    url_for('posts.new_playlist', _external=True),
                    url_for('users.favorites', _external=True)]
    referrer = request.referrer
    flash('You were signed out.')
    if referrer in login_needed:
        return redirect(url_for('main.home'))
    return redirect(referrer)


@users.route('/account', methods=['GET', 'POST'])
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


@users.route('/favorites')
@login_required
def favorites():
    return render_template('favorites.html', faved=current_user.faved, title='Favorites')
