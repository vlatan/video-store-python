from flask import render_template, url_for, flash
from flask import redirect, request, Blueprint, current_app
from flask_login import current_user, login_required
from app import db
from app.users.forms import UpdateAccountForm

users = Blueprint('users', __name__)


@users.route('/favorites')
@login_required
def favorites():
    total = len(posts := [fave.post for fave in current_user.faved])
    return render_template('content.html', posts=posts,
                           total=total, title='Favorites')
