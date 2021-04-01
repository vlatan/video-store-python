import json
import requests
from flask import (render_template, url_for, flash,
                   redirect, request, Blueprint, current_app)
from flask_login import login_user, current_user, logout_user, login_required
from doxapp import db
from doxapp.models import User, Post
from doxapp.users.forms import UpdateAccountForm
from doxapp.users.utils import save_picture, get_google_client_provider

users = Blueprint('users', __name__)


# @users.route('/login/')
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.home'))

#     # define client (Google App) and get provider config
#     client, google_provider_cfg = get_google_client_provider()

#     # check if we got the provider config
#     if google_provider_cfg is None:
#         flash('Unable to authenticate!', 'warning')
#         return redirect(url_for('main.home'))

#     # find out what URL to hit for Google login
#     authorization_endpoint = google_provider_cfg['authorization_endpoint']

#     # use library to construct the request for Google login and provide
#     # scopes that let you retrieve user's profile from Google
#     request_uri = client.prepare_request_uri(
#         authorization_endpoint,
#         redirect_uri=request.base_url + 'callback',
#         scope=['openid', 'email', 'profile']
#     )
#     return redirect(request_uri)


# @users.route('/login/callback')
# def google_callback():
#     # Get authorization code Google sent back to you
#     code = request.args.get('code')

#     # define client (Google App) and get provider config
#     client, google_provider_cfg = get_google_client_provider()

#     # check if we got the provider config
#     if google_provider_cfg is None:
#         flash('Unable to authenticate!', 'warning')
#         return redirect(url_for('main.home'))

#     # Find out what URL to hit to get tokens that allow you to ask for
#     # things on behalf of a user
#     token_endpoint = google_provider_cfg['token_endpoint']

#     # Prepare and send a request to get tokens!
#     token_url, headers, body = client.prepare_token_request(
#         token_endpoint,
#         authorization_response=request.url,
#         redirect_url=request.base_url,
#         code=code
#     )
#     token_response = requests.post(
#         token_url,
#         headers=headers,
#         data=body,
#         auth=(current_app.config['GOOGLE_CLIENT_ID'],
#               current_app.config['GOOGLE_CLIENT_SECRET']),
#     )

#     # Parse the tokens!
#     client.parse_request_body_response(json.dumps(token_response.json()))

#     # Now that you have tokens let's find and hit the URL
#     # from Google that gives you the user's profile information,
#     # including their Google profile image and email
#     userinfo_endpoint = google_provider_cfg['userinfo_endpoint']
#     uri, headers, body = client.add_token(userinfo_endpoint)
#     userinfo_response = requests.get(uri, headers=headers, data=body)

#     # You want to make sure their email is verified.
#     # The user authenticated with Google, authorized your
#     # app, and now you've verified their email through Google!
#     if userinfo_response.json().get('email_verified'):
#         unique_id = userinfo_response.json()['sub']
#         email = userinfo_response.json()['email']
#         picture = userinfo_response.json()['picture']
#         username = userinfo_response.json()['given_name']
#     else:
#         flash('User email not available or not verified by Google.', 'info')
#         return redirect(url_for('main.home'))

#     # search for this user in the database by email
#     user = User.query.filter_by(email=email).first()

#     # Can't find it? Add it to the database.
#     if not user:
#         # Create a user with the information provided by Google
#         user = User(username=username, email=email)
#         # add this new user to the database
#         db.session.add(user)
#         db.session.commit()

#     # Begin user session by logging the user in
#     login_user(user)
#     flash('You are now logged in!', 'success')

#     # Send user back to homepage
#     return redirect(url_for('main.home'))


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
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for(
        'static', filename='profile_pics/' + current_user.image_file)
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
