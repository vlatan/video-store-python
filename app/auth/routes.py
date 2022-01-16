import google_auth_oauthlib.flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import request, redirect, session, current_app
from flask import Blueprint, url_for, flash, render_template
from flask_login import current_user, login_user, logout_user, login_required
from app.auth.helpers import failed_login, get_user_ready

auth = Blueprint('auth', __name__)


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


@auth.route('/authorize')
def authorize():
    # https://developers.google.com/identity/protocols/oauth2/web-server
    CLIENT_CONFIG = current_app.config['GOOGLE_OAUTH_CLIENT_CONFIG']
    CLIENT_ID = current_app.config['GOOGLE_OAUTH_CLIENT_ID']
    REDIRECT_URL = url_for('auth.authorize', _external=True)
    SCOPES = current_app.config['GOOGLE_OAUTH_SCOPES']

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
