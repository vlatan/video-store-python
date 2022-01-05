import os
from flask import current_app
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user
from elasticsearch import Elasticsearch


def admin_required(func):
    @wraps(func)
    def only_admin(*args, **kwargs):
        admin_email = current_app.config['ADMIN_EMAIL']
        if current_user.email != admin_email:
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
    elastic = prep_elastic()
    if not (elastic and elastic.ping()):
        return
    payload = {field: getattr(model, field) for field in model.__searchable__}
    elastic.index(index=index, id=model.id, document=payload)


def remove_from_index(index, model):
    elastic = prep_elastic()
    if not (elastic and elastic.ping()):
        return
    elastic.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    elastic = prep_elastic()
    if not (elastic and elastic.ping()):
        return [], 0
    search = elastic.search(
        index=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']
