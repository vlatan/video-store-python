import requests
from flask import current_app
from functools import wraps
from flask import current_app, flash, redirect, url_for
from flask_login import current_user, login_required
from whoosh.qparser import OrGroup, MultifieldParser
from whoosh.writing import AsyncWriter


def admin_required(func):
    @wraps(func)
    @login_required
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


def add_to_index(obj):
    payload = {field: getattr(obj, field) for field in obj.__searchable__}
    writer = AsyncWriter(current_app.index)
    writer.update_document(id=str(obj.id), **payload)
    writer.commit()


def remove_from_index(obj):
    current_app.index.delete_by_term('id', str(obj.id))


def query_index(fields, keyword, page, per_page):
    with current_app.index.searcher() as searcher:
        schema, og = current_app.index.schema, OrGroup.factory(0.9)
        parser = MultifieldParser(fields, schema, group=og)
        query = parser.parse(keyword)
        results = searcher.search(query)
        exact_len = results.has_exact_length()
        total = len(results) if exact_len else results.estimated_length()
        results = searcher.search_page(query, page, pagelen=per_page)
        ids = [int(result['id']) for result in results]
        return ids, total
