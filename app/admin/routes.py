from flask import Blueprint, render_template
from app.helpers import admin_required
from app.models import User


bp = Blueprint("admin", __name__)


@bp.route("/admin/")
@admin_required
def dashboard():
    users = User.query.all()
    return render_template("admin.html", users=users, title="Admin Dashboard")
