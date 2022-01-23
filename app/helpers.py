import os
from flask import current_app
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from elasticsearch import Elasticsearch
from elasticsearch import ImproperlyConfigured, ElasticsearchException


def admin_required(func):
    @wraps(func)
    def only_admin(*args, **kwargs):
        admin_openid = current_app.config['ADMIN_OPENID']
        if current_user.google_id != admin_openid:
            flash('You need to be admin to access that page!', 'info')
            return redirect(url_for('main.home'))
        return func(*args, **kwargs)
    return only_admin


def dump_datetime(value):
    """ Deserialize datetime object into string form for JSON processing. """
    if value is None:
        return None
    return [value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S")]


def prep_elastic():
    try:
        return current_app.elasticsearch
    except RuntimeError:
        # we're out of the app context, set up elasticsearch manually
        elastic_url = os.environ.get('ELASTICSEARCH_URL')
        return Elasticsearch(elastic_url) if elastic_url else None


def add_to_index(index, model):
    try:
        es = prep_elastic()
        payload = {field: getattr(model, field)
                   for field in model.__searchable__}
        es.index(index=index, id=model.id, document=payload)
    except (AttributeError, ImproperlyConfigured, ElasticsearchException):
        return


def remove_from_index(index, model):
    try:
        es = prep_elastic()
        es.delete(index=index, id=model.id)
    except (AttributeError, ImproperlyConfigured, ElasticsearchException):
        return


def query_index(index, query, page, per_page):
    try:
        es = prep_elastic()
        payload = {'query': {'multi_match': {'query': query, 'fields': ['*']}},
                   'from': (page - 1) * per_page, 'size': per_page}
        search = es.search(index=index, body=payload)

        ids = [int(hit['_id']) for hit in search['hits']['hits']]
        return ids, search['hits']['total']['value']

    except (AttributeError, ImproperlyConfigured, ElasticsearchException):
        # there was a problem with elasticserach
        # you may need to log this error
        return [], 0
