import os
import hashlib
import requests
from urllib.parse import urlencode
from google_auth_oauthlib.flow import Flow
from flask import request, redirect, session, current_app
from flask import Blueprint, url_for, flash, render_template
from flask_login import current_user, logout_user, login_required
from app.auth.helpers import failed_login, finalize_google_login, finalize_fb_login

auth = Blueprint("auth", __name__)


@auth.route("/authorize/google")
def google():
    """
    Use Google to authenticate the user.
    https://developers.google.com/identity/protocols/oauth2/web-server/
    """

    CLIENT_CONFIG = current_app.config["GOOGLE_CLIENT_CONFIG"]
    REDIRECT_URL = url_for("auth.google", _external=True)
    SCOPES = current_app.config["GOOGLE_SCOPES"]

    # if the request DOESN'T have 'code' argument in the URL
    if "code" not in request.args:

        # do not proceed if user is already logged in
        if current_user.is_authenticated:
            return redirect(request.referrer)

        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
        flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = REDIRECT_URL

        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type="offline",
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes="true",
        )

        # Store the state so the callback can verify the auth server response.
        session["state"] = state

        # redirect user to the callback url which is in fact this exact same view
        return redirect(authorization_url)

    # Create flow instance
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, state=session["state"])
    flow.redirect_uri = REDIRECT_URL

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    try:
        # verify ID token, log in user
        finalize_google_login(credentials)
        # successfully completed the process
        return render_template("bingo_popup.html")

    except Exception:
        # Invalid token, failed to complete the process, signal to the parent window
        return render_template("bummer_popup.html")


@auth.route("/authorize/onetap", methods=["POST"])
def onetap():
    """
    Use Google's One Tap to authenticate the user.
    https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
    """

    if current_user.is_authenticated:
        return redirect(request.referrer)

    csrf_token_cookie = request.cookies.get("g_csrf_token")
    if not csrf_token_cookie:
        # No CSRF token in Cookie.
        return failed_login()
    csrf_token_body = request.form.get("g_csrf_token")
    if not csrf_token_body:
        # No CSRF token in post body.
        return failed_login()
    if csrf_token_cookie != csrf_token_body:
        # Failed to verify double submit cookie.
        return failed_login()

    try:
        # get the ID token
        token = request.form.get("credential")
        # verify ID token, get user info, log user in
        finalize_google_login(token)
        # successfully completed the process
        return redirect(request.referrer)

    except Exception:
        # invalid token
        return failed_login()


@auth.route("/authorize/facebook")
def facebook():
    """
    Use Facebook to authenticate the user.
    https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow
    """

    CLIENT_ID = current_app.config["FB_CLIENT_ID"]
    REDIRECT_URI = url_for("auth.facebook", _external=True)

    # check if this view has 'code' argument in it
    if not (CODE := request.args.get("code")):

        # do not proceed if user is already logged in
        if current_user.is_authenticated:
            return redirect(request.referrer)

        # create an anti-forgery unique token
        STATE = hashlib.sha256(os.urandom(1024)).hexdigest()
        # put it in a session
        session["state"] = STATE

        # oauth dialog endpoint
        dialog_endpoint = current_app.config["FB_DIALOG_ENDPOINT"]
        # parameters to add to the the dialog endpoint
        payload = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "state": STATE,
            "auth_type": "rerequest",
            "scope": "email",
        }
        # construct the final dialog uri
        dialog_uri = os.path.join(dialog_endpoint, "?", urlencode(payload))
        # redirect to the dialog uri
        return redirect(dialog_uri)

    try:
        # check if the anti-forgery unique session token is valid
        if request.args.get("state") != session["state"]:
            # failed to complete the process
            raise ValueError

        # exchange the code for access token
        CLIENT_SECRET = current_app.config["FB_CLIENT_SECRET"]
        access_token_endpoint = current_app.config["FB_ACCESS_TOKEN_ENDPOINT"]
        # parameters for the access token endpoint
        payload = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "client_secret": CLIENT_SECRET,
            "code": CODE,
        }

        # get access token from the access token endpoint (json response)
        ACCESS_TOKEN = requests.get(access_token_endpoint, params=payload)
        ACCESS_TOKEN = ACCESS_TOKEN.json()["access_token"]

        # verify the access token we got
        inspect_token_endpoint = current_app.config["FB_INSPECT_TOKEN_ENDPOINT"]
        # parameters for the inspect token endpoint
        payload = {
            "input_token": ACCESS_TOKEN,
            "access_token": f"{CLIENT_ID}|{CLIENT_SECRET}",
        }

        # get response from the inspect token endpoint (json response)
        data = requests.get(inspect_token_endpoint, params=payload).json()["data"]
        # this will be True if access token is valid
        if not data.get("is_valid"):
            # failed to complete the process (invalid access token)
            raise ValueError

        # get user info
        USER_ID = data["user_id"]
        GRAPH_ENDPOINT = current_app.config["FB_GRAPH_ENDPOINT"]
        user_graph_endpoint = f"{GRAPH_ENDPOINT}/{USER_ID}"
        # parameters for the graph endpoint
        payload = {
            "access_token": ACCESS_TOKEN,
            "fields": "id,first_name,picture,email",
        }

        # get response from the graph endpoint (json response)
        data = requests.get(user_graph_endpoint, params=payload).json()

        # process user data for login
        pic = data.get("picture", {}).get("data", {}).get("url")
        user_info = {
            "token": ACCESS_TOKEN,
            "facebook_id": USER_ID,
            "email": data.get("email"),
            "name": data.get("first_name", "Guest"),
            "picture": pic,
        }

        # get user ready, log user in
        finalize_fb_login(user_info)
        # successfully completed the process
        return render_template("bingo_popup.html")

    except Exception:
        # failed to complete the process, signal to the parent window
        return render_template("bummer_popup.html")


@auth.route("/logout")
@login_required
def logout():
    """Logout the user and redirect."""

    logout_user()
    login_needed = [
        url_for("users.liked", _external=True),
        url_for("posts.new_post", _external=True),
        url_for("lists.new_playlist", _external=True),
        url_for("users.favorites", _external=True),
    ]
    referrer = request.referrer
    flash("You've been logged out!", "info")
    if referrer in login_needed:
        return redirect(url_for("main.home"))
    return redirect(referrer)
