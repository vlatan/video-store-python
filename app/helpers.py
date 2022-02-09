import os
import requests
from flask import current_app
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from elasticsearch import ImproperlyConfigured, ElasticsearchException


def admin_required(func):
    @wraps(func)
    def only_admin(*args, **kwargs):
        admin_openid = current_app.config['ADMIN_OPENID']
        if current_user.google_id != admin_openid:
            flash('Sorry, it seems you don\'t have access to that page!', 'info')
            return redirect(url_for('main.home'))
        return func(*args, **kwargs)
    return only_admin


def save_image(image_url, file_path):
    response = requests.get(image_url)
    if response.ok:
        with open(file_path, 'wb') as file:
            file.write(response.content)
            return True
    return False


def dump_datetime(value):
    """ Deserialize datetime object into string form for JSON processing. """
    return [value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S")] if value else None


def add_to_index(index, model):
    try:
        es = current_app.elasticsearch
        payload = {field: getattr(model, field)
                   for field in model.__searchable__}
        es.index(index=index, id=model.id, document=payload)
    except (AttributeError, ImproperlyConfigured, ElasticsearchException):
        return


def remove_from_index(index, model):
    try:
        es = current_app.elasticsearch
        es.delete(index=index, id=model.id)
    except (AttributeError, ImproperlyConfigured, ElasticsearchException):
        return


def query_index(index, query, page, per_page):
    try:
        es = current_app.elasticsearch
        payload = {'query': {'multi_match': {'query': query, 'fields': ['*']}},
                   'from': (page - 1) * per_page, 'size': per_page}
        search = es.search(index=index, body=payload)

        ids = [int(hit['_id']) for hit in search['hits']['hits']]
        return ids, search['hits']['total']['value']

    except (AttributeError, ImproperlyConfigured, ElasticsearchException):
        # you may need to log this error
        return [], 0
