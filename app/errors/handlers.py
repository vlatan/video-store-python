from flask import Blueprint, render_template
from oauthlib.oauth2.rfc6749.errors import MismatchingStateError


bp = Blueprint("errors", __name__)


@bp.app_errorhandler(403)
def error_403(error):
    heading = "You don't have permission to do that (403)"
    text = "Please check your account and try again."
    return render_template("error.html", title="403", heading=heading, text=text), 403


@bp.app_errorhandler(404)
def error_404(error):
    heading = "Oops. Page not found (404)"
    text = "That page does not exist. Please try a different location."
    return render_template("error.html", title="404", heading=heading, text=text), 404


@bp.app_errorhandler(405)
def error_403(error):
    heading = "You don't have permission to do that (405)"
    text = "Please check your account and try again."
    return render_template("error.html", title="405", heading=heading, text=text), 405


@bp.app_errorhandler(500)
@bp.app_errorhandler(MismatchingStateError)
def error_500(error):
    heading = "Something went wrong (500)"
    text = (
        "We are experiencing some trouble on our end. "
        "Please try again in near future."
    )
    return render_template("error.html", title="500", heading=heading, text=text), 500
