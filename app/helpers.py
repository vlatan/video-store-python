import functools
from whoosh.writing import AsyncWriter
from whoosh.qparser import OrGroup, MultifieldParser
from googleapiclient.discovery import build as google_discovery_build

from flask_login import current_user, login_required
from flask import current_app, flash, redirect, url_for


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


def add_to_index(obj):
    payload = {field: getattr(obj, field) for field in obj.__searchable__}
    writer = AsyncWriter(current_app.config["search_index"])
    writer.update_document(id=str(obj.id), **payload)
    writer.commit()


def remove_from_index(obj):
    writer = AsyncWriter(current_app.config["search_index"])
    writer.delete_by_term("id", str(obj.id))
    writer.commit()


def query_index(fields, keyword, page, per_page):
    with current_app.config["search_index"].searcher() as searcher:
        schema, og = current_app.config["search_index"].schema, OrGroup.factory(0.9)
        parser = MultifieldParser(fields, schema, group=og)
        query = parser.parse(keyword)
        total = len(searcher.search(query))
        results = searcher.search_page(query, page, pagelen=per_page)
        ids = [int(result["id"]) for result in results]
        return ids, total


def query_index_all(fields, keyword):
    with current_app.config["search_index"].searcher() as searcher:
        schema, og = current_app.config["search_index"].schema, OrGroup.factory(0.9)
        parser = MultifieldParser(fields, schema, group=og)
        query = parser.parse(keyword)
        results = searcher.search(query, limit=None)
        return [int(result["id"]) for result in results]
