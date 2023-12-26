import functools
from googleapiclient.discovery import build as google_discovery_build
from redis.commands.search.query import Query

from flask_login import current_user, login_required
from flask import current_app, flash, redirect, url_for, json


def admin_required(func):
    @functools.wraps(func)
    @login_required
    def only_admin(*args, **kwargs):
        if current_user.google_id == current_app.config["ADMIN_OPENID"]:
            return func(*args, **kwargs)
        flash("Sorry, it seems you don't have access to that page!", "info")
        return redirect(url_for("main.home"))

    return only_admin


def dump_datetime(value):
    """Deserialize datetime object into string form for JSON processing."""
    return [value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S")] if value else None


def youtube_build():
    """Instantiate google discovery build object."""
    return google_discovery_build(
        serviceName="youtube",
        version="v3",
        developerKey=current_app.config["YOUTUBE_API_KEY"],
        cache_discovery=False,
    )
