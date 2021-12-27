from flask import current_app
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user


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


def add_to_index(index, model):
    if not current_app.elasticsearch:
        return
    payload = {field: model.field for field in model.__searchable__}
    current_app.elasticsearch.index(index=index, id=model.id, document=payload)


def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query):
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index,
        query={'multi_match': {'query': query, 'fields': ['*']}})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']
