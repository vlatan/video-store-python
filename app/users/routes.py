from flask import render_template, url_for, flash
from flask import redirect, request, Blueprint
from flask_login import current_user, login_required
from app import db
from app.users.forms import UpdateAccountForm

users = Blueprint('users', __name__)


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
    posts = [fave.post for fave in current_user.faved]
    return render_template('content.html', posts=posts, title='Favorites')
