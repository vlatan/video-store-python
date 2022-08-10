from flask import Blueprint, render_template
from app.helpers import admin_required

admin = Blueprint("admin", __name__)


@admin.route("/admin/")
@admin_required
def dashboard():
    return render_template("admin.html")
