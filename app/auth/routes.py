import os
import hashlib
import requests
import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import request, redirect, session, current_app
from flask import Blueprint, url_for, flash, render_template
from flask_login import current_user, login_user, logout_user, login_required
from app.auth.helpers import failed_login, get_user_ready
from app.models import User

auth = Blueprint('auth', __name__)


@auth.route('/authorize/google')
def google():
    # https://developers.google.com/identity/protocols/oauth2/web-server
    CLIENT_CONFIG = current_app.config['GOOGLE_CLIENT_CONFIG']
    CLIENT_ID = current_app.config['GOOGLE_CLIENT_ID']
    REDIRECT_URL = url_for('auth.google', _external=True)
    SCOPES = current_app.config['GOOGLE_SCOPES']

    # if the request DOESN'T have 'code' argument in the URL
    if 'code' not in request.args:

        if current_user.is_authenticated:
            return redirect(request.referrer)

        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = REDIRECT_URL

        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true')

        # Store the state so the callback can verify the auth server response.
        session['state'] = state

        return redirect(authorization_url)

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES, state=session['state'])
    flow.redirect_uri = REDIRECT_URL

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    try:
        # verify the integrity of the ID token and return the user info
        # https://google-auth.readthedocs.io/en/stable/reference/google.oauth2.id_token.html#google.oauth2.id_token.verify_oauth2_token
        user_info = id_token.verify_oauth2_token(
            credentials.id_token, google_requests.Request(), CLIENT_ID)
        # check if there's user ID, if not it will raise ValueError
        openid = user_info['sub']
    except ValueError:
        # Invalid token
        return render_template('close_oauth.html')

    user = get_user_ready(openid, user_info)
    # begin user session by logging the user in
    login_user(user, remember=True)

    # store revoke token in session in case the user want's to revoke access
    session['revoke_token'] = credentials.token

    return render_template('close_oauth.html')


@auth.route('/authorize/onetap', methods=['POST'])
def onetap():
    if current_user.is_authenticated:
        return redirect(request.referrer)

    csrf_token_cookie = request.cookies.get('g_csrf_token')
    if not csrf_token_cookie:
        # No CSRF token in Cookie.
        return failed_login()
    csrf_token_body = request.form.get('g_csrf_token')
    if not csrf_token_body:
        # No CSRF token in post body.
        return failed_login()
    if csrf_token_cookie != csrf_token_body:
        # Failed to verify double submit cookie.
        return failed_login()

    try:
        # verify the integrity of the ID token and get the user info
        token = request.form.get('credential')
        CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
        # https://google-auth.readthedocs.io/en/stable/reference/google.oauth2.id_token.html#google.oauth2.id_token.verify_oauth2_token
        user_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), CLIENT_ID)
        # check if there's user ID, if not it will raise ValueError
        openid = user_info['sub']
    except ValueError:
        # Invalid token
        return failed_login()

    user = get_user_ready(openid, user_info)
    # begin user session by logging the user in
    login_user(user, remember=True)
    return redirect(request.referrer)


@auth.route('/authorize/facebook')
def facebook():
    # https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow#login

    CLIENT_ID = current_app.config['FB_CLIENT_ID']
    REDIRECT_URI = url_for('auth.facebook', _external=True)

    # check if this view has 'code' argument in it
    if not (CODE := request.args.get('code')):

        # do not proceed if user is already logged in
        if current_user.is_authenticated:
            return redirect(request.referrer)

        DIALOG_ENDPOINT = 'https://www.facebook.com/v12.0/dialog/oauth'
        # create an anti-forgery unique token
        STATE = hashlib.sha256(os.urandom(1024)).hexdigest()
        # put it in a session
        session['state'] = STATE
        # construct the dialog url
        dialog_uri = (f'{DIALOG_ENDPOINT}?response_type=code&'
                      f'client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&'
                      f'state={STATE}&auth_type=rerequest&scope=email')
        # redirect to the dialog uri
        return redirect(dialog_uri)

    # check if the anti-forgery unique session token is valid
    if request.args.get('state') != session['state']:
        # failed to complete the process
        return render_template('close_oauth.html')

    try:
        # exchange the code for access token
        ACCESS_TOKEN_ENDPOINT = 'https://graph.facebook.com/v12.0/oauth/access_token'
        CLIENT_SECRET = current_app.config['FB_CLIENT_SECRET']
        access_token_uri = (f'{ACCESS_TOKEN_ENDPOINT}?'
                            f'client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&'
                            f'client_secret={CLIENT_SECRET}&code={CODE}')
        # get response from the access_token_uri
        credentials = requests.get(access_token_uri).json()

        if not (ACCESS_TOKEN := credentials.get('access_token')):
            # failed to complete the process
            raise KeyError

        # verify the access token we got
        INSPECT_TOKEN_ENDPOINT = 'https://graph.facebook.com/debug_token'
        inspect_token_uri = (f'{INSPECT_TOKEN_ENDPOINT}?input_token={ACCESS_TOKEN}&'
                             f'access_token={CLIENT_ID}|{CLIENT_SECRET}')
        # get response from the inspect_token_uri
        data = requests.get(inspect_token_uri).json().get('data')

        if not (data and data.get('is_valid') and (USER_ID := (data.get('user_id')))):
            # failed to complete the process
            raise KeyError

        # get user info
        GRAPH_ENDPOINT = 'https://graph.facebook.com/v12.0/'
        user_info_uri = (f'{GRAPH_ENDPOINT}{USER_ID}?access_token={ACCESS_TOKEN}&'
                         'fields=id,first_name,picture,email')
        # get response from the user_info_uri
        user_info = requests.get(user_info_uri).json()

        if user_info:
            # grab the first user for testing
            user = User.query.first()
            # begin user session by logging the user in
            login_user(user, remember=True)
    except Exception:
        # failed to complete the process
        return render_template('close_oauth.html')

    return render_template('close_oauth.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    login_needed = [url_for('users.account', _external=True),
                    url_for('posts.new_post', _external=True),
                    url_for('posts.new_playlist', _external=True),
                    url_for('users.favorites', _external=True)]
    referrer = request.referrer
    flash('You\'ve been logged out!', 'info')
    if referrer in login_needed:
        return redirect(url_for('main.home'))
    return redirect(referrer)
