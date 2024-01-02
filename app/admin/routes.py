from concurrent.futures import as_completed, ThreadPoolExecutor
from flask import Blueprint, render_template, current_app

from app.models import User
from app.main.routes import avatar
from app.helpers import admin_required


bp = Blueprint("admin", __name__)


@bp.route("/admin/")
@admin_required
def dashboard() -> str:
    """Get Admin dashboard."""

    # get all users, TODO: paginate
    users = User.query.all()

    redis_client = current_app.config["REDIS_CLIENT"]

    # Download users avatars in parallel if necessary
    # and attach the avatar_url to user object
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(avatar, user, redis_client): user for user in users}

        users = []
        for future in as_completed(futures):
            user = futures[future]
            user.avatar_url = future.result()
            users.append(user)

    # sort users by created_at
    users = sorted(users, key=lambda user: user.created_at)

    return render_template("admin.html", users=users, title="Admin Dashboard")
