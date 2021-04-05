# https://realpython.com/flask-google-login/
# https://www.youtube.com/playlist?list=PL-osiE80TeTs4UjLw5MM6OjgkjFeUxCYH
# https://www.youtube.com/watch?v=goToXTC96Co

# https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow
# https://www.toptal.com/flask/flask-login-tutorial-sso

# https://flask-dance.readthedocs.io/en/latest/quickstart.html

# https://www.w3schools.com/howto/tryit.asp?filename=tryhow_css_social_login
# https://www.tutorialrepublic.com/codelab.php?topic=bootstrap-3&file=sign-in-from-with-social-login-button
# https://bbbootstrap.com/snippets/signin-form-social-login-72108315
# https://jsfiddle.net/StartBootstrap/amxr8n19/

# https://developers.google.com/identity/gsi/web/guides/overview
# https://developers.google.com/identity/protocols/oauth2/web-server#httprest_5
# https://developers.google.com/identity/protocols/oauth2/scopes#oauth2
# https://developers.google.com/identity/protocols/oauth2/openid-connect#id_token-name
# https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html


# https://stackoverflow.com/questions/51601915/how-to-use-the-google-api-without-checking-a-client-secret-json-into-version-con
# https://developers.google.com/identity/protocols/oauth2/web-server

import os
from doxapp import create_app

app = create_app()

if __name__ == '__main__':
    app.run('localhost', debug=True)
