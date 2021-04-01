import os
import requests
import secrets
from PIL import Image
from oauthlib.oauth2 import WebApplicationClient
from flask import current_app


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(
        current_app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def get_google_client_provider():
    try:
        # define Google client
        client = WebApplicationClient(current_app.config['GOOGLE_CLIENT_ID'])
        # get the provider's (our Google App) config
        provider = requests.get(
            current_app.config['GOOGLE_DISCOVERY_URL']).json()
        return client, provider
    except:
        return None
