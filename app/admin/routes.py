from flask import Blueprint, url_for, render_template
from app.helpers import admin_required

admin = Blueprint("admin", __name__)


@admin.route("/admin/")
@admin_required
def admin():
    pass
