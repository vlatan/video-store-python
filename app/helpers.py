import functools
from typing import Callable
from googleapiclient.discovery import build as google_discovery_build

from werkzeug.wrappers.response import Response
from flask_login import current_user, login_required
from flask import current_app, flash, redirect, url_for, make_response


def admin_required(func) -> Callable:
    @functools.wraps(func)
    @login_required
    def only_admin(*args, **kwargs) -> Response:
        if current_user.google_id == current_app.config["ADMIN_OPENID"]:
            return func(*args, **kwargs)
        flash("Sorry, it seems you don't have access to that page!", "info")
        return redirect(url_for("main.home"))

    return only_admin


def dump_datetime(value) -> list[str] | None:
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


def serve_as(content_type="text/html", charset="utf-8") -> Callable:
    """Modify response's content-type header."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Response:
            template = func(*args, **kwargs)
            response = make_response(template)
            response.headers["content-type"] = f"{content_type}; charset={charset}"
            return response

        return wrapper

    return decorator
