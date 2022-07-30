import os
import hashlib
import requests
from datetime import timedelta
from urllib.parse import urlencode
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import request, redirect, session, current_app
from flask import Blueprint, url_for, flash, render_template
from flask_login import current_user, login_user, logout_user, login_required
from app.auth.helpers import failed_login, get_user_ready

auth = Blueprint("auth", __name__)


@auth.route("/authorize/google")
def google():
    # https://tinyurl.com/ymadyw2k
    CLIENT_CONFIG = current_app.config["GOOGLE_CLIENT_CONFIG"]
    CLIENT_ID = current_app.config["GOOGLE_CLIENT_ID"]
    REDIRECT_URL = url_for("auth.google", _external=True)
    SCOPES = current_app.config["GOOGLE_SCOPES"]

    # if the request DOESN'T have 'code' argument in the URL
    if "code" not in request.args:

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

        return redirect(authorization_url)

    # Create flow instance
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, state=session["state"])
    flow.redirect_uri = REDIRECT_URL

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    try:
        # verify the integrity of the ID token and return the user info
        # https://tinyurl.com/z2b5xr25, https://tinyurl.com/3dwm6pxe
        token, google_request = credentials.id_token, google_requests.Request()
        data = id_token.verify_oauth2_token(token, google_request, CLIENT_ID)

        # process user data for login
        user_info = {
            "google_id": data["sub"],
            "email": data.get("email"),
            "name": data.get("given_name", "Guest"),
            "picture": data.get("picture"),
        }

        # get user ready (create or update their info)
        user = get_user_ready(user_info)
        # begin user session by logging the user in
        login_user(user, remember=True, duration=timedelta(days=30))
        # store revoke token in session in case the user wants to revoke access
        session["revoke_token"] = credentials.token
        # successfully completed the process
        return render_template("bingo_popup.html")

    except Exception:
        # Invalid token
        # Failed to complete the process, signal to the parent window
        return render_template("bummer_popup.html")


@auth.route("/authorize/onetap", methods=["POST"])
def onetap():
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
        # verify the integrity of the ID token and get the user info
        token = request.form.get("credential")
        google_request = google_requests.Request()
        CLIENT_ID = current_app.config["GOOGLE_OAUTH_CLIENT_ID"]
        # https://tinyurl.com/z2b5xr25, https://tinyurl.com/3dwm6pxe
        data = id_token.verify_oauth2_token(token, google_request, CLIENT_ID)

        # process user data for login
        user_info = {
            "google_id": data["sub"],
            "email": data.get("email"),
            "name": data.get("given_name", "Guest"),
            "picture": data.get("picture"),
        }

        # get user ready (create or update their info)
        user = get_user_ready(user_info)
        # begin user session by logging the user in
        login_user(user, remember=True, duration=timedelta(days=30))
        # successfully completed the process
        return redirect(request.referrer)

    except Exception:
        # Invalid token
        return failed_login()


@auth.route("/authorize/facebook")
def facebook():
    # https://tinyurl.com/yzexjyru

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

        # prepare the dialog uri
        dialog_endpoint = "https://www.facebook.com/v12.0/dialog/oauth"
        # parameters to the dialog endpoint
        payload = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "state": STATE,
            "auth_type": "rerequest",
            "scope": "email",
        }

        dialog_uri = f"{dialog_endpoint}?{urlencode(payload)}"

        # redirect to the dialog endpoint
        return redirect(dialog_uri)

    try:
        # check if the anti-forgery unique session token is valid
        if request.args.get("state") != session["state"]:
            # failed to complete the process
            raise ValueError

        # exchange the code for access token
        CLIENT_SECRET = current_app.config["FB_CLIENT_SECRET"]
        access_token_endpoint = "https://graph.facebook.com/v12.0/oauth/access_token"
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
        inspect_token_endpoint = "https://graph.facebook.com/debug_token"
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
        graph_endpoint = f"https://graph.facebook.com/v12.0/{USER_ID}"
        # parameters for the graph endpoint
        payload = {
            "access_token": ACCESS_TOKEN,
            "fields": "id,first_name,picture,email",
        }

        # get response from the graph endpoint (json response)
        data = requests.get(graph_endpoint, params=payload).json()

        # process user data for login
        pic = data.get("picture", {}).get("data", {}).get("url")
        user_info = {
            "facebook_id": USER_ID,
            "email": data.get("email"),
            "name": data.get("first_name", "Guest"),
            "picture": pic,
        }

        # get user ready (create or update their info)
        user = get_user_ready(user_info)
        # begin user session by logging the user in
        login_user(user, remember=True, duration=timedelta(days=30))
        # store revoke token in session in case the user wants to revoke access
        session["revoke_token"] = ACCESS_TOKEN
        # successfully completed the process
        return render_template("bingo_popup.html")

    except Exception:
        # failed to complete the process, signal to the parent window
        return render_template("bummer_popup.html")


@auth.route("/logout")
@login_required
def logout():
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
