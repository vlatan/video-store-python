import string
import functools
from googleapiclient.discovery import build as google_discovery_build
from redis.commands.search.query import Query

from flask_login import current_user, login_required
from flask import current_app, flash, redirect, url_for, json


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
    search_index = current_app.config["search_index"]
    document = {field: json.dumps(getattr(obj, field)) for field in obj.__searchable__}
    search_index.add_document(doc_id=str(obj.id), replace=True, **document)


def remove_from_index(obj):
    search_index = current_app.config["search_index"]
    search_index.delete_document(str(obj.id), delete_actual_document=True)


def query_index(phrase: str, page: int, per_page: int) -> tuple[list[int], int]:
    """Return offset and number of search results from the index for a given phrase."""
    # get RedisSearch search index
    search_index = current_app.config["search_index"]
    # remove punctuation from phrase
    words = phrase.translate(str.maketrans("", "", string.punctuation))
    # divide words with pipe symbol (designating OR)
    words = " | ".join(words.split())
    # make query object with offset and number of documents
    query = Query(words).paging(offset=page * per_page, num=per_page)
    # get search result
    search_result = search_index.search(query)
    # get ids from the results
    ids = [int(document.id) for document in search_result.docs]
    # return ids and total items fetched
    return ids, int(search_result.total)


def query_index_all(phrase: str) -> list[int]:
    """Return all search result from the index."""
    search_index = current_app.config["search_index"]
    words = phrase.translate(str.maketrans("", "", string.punctuation))
    words = " | ".join(words.split())
    query = Query(words).paging(offset=0, num=3000)
    search_result = search_index.search(query).docs
    return [int(document.id) for document in search_result]
