import time
import logging
from threading import Thread
from celery import shared_task
from googleapiclient.errors import HttpError
from wtforms.validators import ValidationError
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.exc import IntegrityError, StatementError

from flask import Flask, current_app
from flask.ctx import AppContext

from app import db
from app.models import Post, Playlist
from app.helpers import youtube_build
from app.posts.helpers import validate_video
from app.cron.helpers import get_playlist_videos
from app.sources.helpers import validate_playlist


def get_youtube_videos():
    all_videos, complete = [], True
    # get all playlists from db
    playlists = Playlist.query.all()
    # construct youtube API service
    with youtube_build() as youtube:
        # loop through the playlists
        for playlist in playlists:
            # refresh playlist thumbs
            source_info = validate_playlist(playlist.playlist_id, youtube)
            playlist.channel_thumbnails = source_info["channel_thumbnails"]
            db.session.commit()
            time.sleep(1)
            # get playlist VALID videos from YT
            playlist_videos, done = get_playlist_videos(playlist.playlist_id, youtube)
            if not done:
                complete = False
            # loop through the videos in this playlist
            for video in playlist_videos:
                # add relationship with this playlist to the video metadata
                video["playlist"] = playlist
            # add this batch of videos to the total list of videos
            all_videos += playlist_videos

    # remove duplicates if any
    all_videos = list({v["video_id"]: v for v in all_videos}.values())
    # sort by upload date
    all_videos = sorted(all_videos, key=lambda d: d["upload_date"])

    return all_videos, complete


def revalidate_single_video(post):
    with youtube_build() as youtube:
        try:
            scope = {
                "id": post.video_id,
                "part": ["status", "snippet", "contentDetails"],
            }
            req = youtube.videos().list(**scope)
            # this will raise IndexError if ['items'] is empty list``
            # which means the video does not exist
            res = req.execute()["items"][0]
            # this will raise ValidationError if video's invalid
            validate_video(res)
        # video is not validated or doesn't exist at YouTube
        except (IndexError, ValidationError):
            try:
                db.session.delete(post)
                db.session.commit()
            except (ObjectDeletedError, StatementError):
                db.session.rollback()
        except HttpError:
            # we couldn't connect to YouTube API,
            # so we can't evaluate the video
            pass


@shared_task
def process_videos():
    PER_PAGE = current_app.config["NUM_RELATED_POSTS"]

    # get all VALID videos from our playlists from YouTube
    all_videos, complete = get_youtube_videos()

    # loop through total number of videos
    for video in all_videos:
        # take a short break before processing the next video
        time.sleep(1.2)

        # if video is already posted
        if posted := Post.query.filter_by(video_id=video["video_id"]).first():
            # if it doesn't match the playlist id
            if posted.playlist_id != video["playlist_id"]:
                # match playlist id
                posted.playlist_id = video["playlist_id"]
                # associate with existing playlist in our db
                posted.playlist = video["playlist"]
                db.session.commit()

            # update similar_ids if there's a change
            similar = Post.get_related_posts(posted.title, PER_PAGE)
            similar = [item["id"] for item in similar]
            if posted.similar != similar:
                posted.similar = similar
                db.session.commit()

            # update short description if the title was manually edited
            if (title := video["title"]) != posted.title:
                if short_desc := generate_description(title):
                    posted.short_description = short_desc
                    db.session.commit()

            # if there is NO short description in DB generate one
            elif not posted.short_description:
                if short_desc := generate_description(posted.title):
                    posted.short_description = short_desc
                    db.session.commit()

            # TODO: Categorize the video using generative AI

        else:
            if short_desc := generate_description(video["title"]):
                video["short_description"] = short_desc

            # TODO: Categorize the video using generative AI

            # create object from Model
            post = Post(**video)
            try:
                db.session.add(post)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    # get sources ids
    sources = [pl.playlist_id for pl in Playlist.query.all()]

    # delete missing videos if all VALID videos are fetched from YT
    if complete:
        fetched_ids = {video["video_id"] for video in all_videos}
        posted = Post.query.filter(Post.playlist_id.in_(sources)).all()
        posted_ids = {post.video_id for post in posted}
        to_delete = posted_ids - fetched_ids
        to_delete = Post.query.filter(Post.video_id.in_(to_delete)).all()
        for post in to_delete:
            try:
                db.session.delete(post)
                db.session.commit()
            except (ObjectDeletedError, StatementError):
                db.session.rollback()
            time.sleep(1)

    # revalidate orphan videos (not attached to any source/playlist)
    orphan_posts = Post.query.filter(
        (Post.playlist_id == None) | (Post.playlist_id.not_in(sources))
    ).all()
    for post in orphan_posts:
        revalidate_single_video(post)
        time.sleep(1)


def reindex(app_context: AppContext) -> None:
    if not app_context:
        return

    with app_context:
        Post.reindex()


def populate_search_index(app: Flask) -> None:
    """Populate the app search index."""
    # exit if no search index object in app config
    if not (search_index := app.config.get("search_index")):
        return

    # exit if there's no search index object
    if not search_index.is_empty():
        return

    # reindex the app in a thread, send app context in the thread
    thread = Thread(target=reindex, name="search_index", args=[app.app_context()])
    thread.start()


def generate_description(title: str) -> str | None:
    """Generate description from a generative AI given a title."""

    generate_content = current_app.config["generate_content"]
    prompt = f"Write a short text about: {title}."

    try:
        return generate_content(prompt).text
    except (KeyError, IndexError) as e:
        logging.warning(f"Was unable to generate a summary for: {title}")
        logging.warning(str(e))
        return None


def categorize(title: str, categories: str) -> str | None:
    """Generate a category from a generative AI based given a title and categories."""

    generate_content = current_app.config["generate_content"]
    prompt = f'Select a category for the documentary "{title}" from these categories: {categories}.'

    try:
        return generate_content(prompt).text
    except (KeyError, IndexError) as e:
        logging.warning(f"Was unable to generate category for: {title}")
        logging.warning(str(e))
        return None
