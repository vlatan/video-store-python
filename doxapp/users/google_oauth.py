from flask import flash
from flask_login import current_user, login_user
from flask_dance.contrib.google import make_google_blueprint
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from sqlalchemy.orm.exc import NoResultFound
from doxapp.models import db, User, OAuth


google_bp = make_google_blueprint(
    scope=['profile', 'email'],
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user),
)


# create/login local user on successful OAuth login
@oauth_authorized.connect_via(google_bp)
def google_logged_in(google_bp, token):
    if not token:
        flash('Failed to log in.', category='error')
        return False

    resp = google_bp.session.get('/oauth2/v1/userinfo')
    if not resp.ok:
        flash('Failed to fetch user info.', category='error')
        return False

    info = resp.json()
    user_id = info['id']

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=google_bp.name, provider_user_id=user_id)
    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(provider=google_bp.name,
                      provider_user_id=user_id,
                      token=token)

    if oauth.user:
        login_user(oauth.user)
        flash(f'Successfully signed in. {info}', category='success')

    else:
        # Create a new local user account for this user
        user = User(username=info['given_name'], email=info['email'])
        # Associate the new local user account with the OAuth token
        oauth.user = user
        # Save and commit our database models
        db.session.add_all([user, oauth])
        db.session.commit()
        # Log in the new local user account
        login_user(user)
        flash(f'Successfully signed in. {info}', category='success')

    # Disable Flask-Dance's default behavior for saving the OAuth token
    return False


# notify on OAuth provider error
@oauth_error.connect_via(google_bp)
def google_error(google_bp, message, response):
    msg = f'OAuth error from {google_bp.name}! message={message} response={response}'
    flash(msg, category='error')
