import time
import atexit
from flask import current_app
from wtforms.validators import ValidationError
from app import db
from app.models import Post, Playlist
from app.cron.helpers import get_playlist_videos
from app.posts.helpers import validate_video
from app.sources.helpers import validate_playlist
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Thread
from pytz import utc
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm.exc import ObjectDeletedError


def get_youtube_videos(api_key):
    all_videos, complete = [], True
    # get all playlists from db
    playlists = Playlist.query.all()
    # construct youtube API service
    with build("youtube", "v3", developerKey=api_key, cache_discovery=False) as youtube:
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


def revalidate_single_video(post, api_key):
    with build("youtube", "v3", developerKey=api_key, cache_discovery=False) as youtube:
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


def process_videos(app):
    with app.app_context():
        API_KEY = current_app.config["YOUTUBE_API_KEY"]
        PER_PAGE = current_app.config["NUM_RELATED_POSTS"]

        # get all VALID videos from our playlists from YouTube
        all_videos, complete = get_youtube_videos(API_KEY)

        # loop through total number of videos
        for video in all_videos:
            # if video is already posted
            if posted := Post.query.filter_by(video_id=video["video_id"]).first():
                # if it doesn't match the playlist id
                if posted.playlist_id != video["playlist_id"]:
                    # match playlist id
                    posted.playlist_id = video["playlist_id"]
                    # associate with existing playlist in our db
                    posted.playlist = video["playlist"]
                    db.session.commit()
                    time.sleep(1)

                # update similar_ids if there's a change
                similar = Post.get_related_posts(posted.title, PER_PAGE)
                similar = [item["id"] for item in similar]
                if posted.similar != similar:
                    posted.similar = similar
                    db.session.commit()
                    time.sleep(1)

            else:
                # create object from Model
                post = Post(**video)
                try:
                    db.session.add(post)
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                time.sleep(1)

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
            revalidate_single_video(post, API_KEY)
            time.sleep(1)


def init_scheduler_jobs():
    # https://stackoverflow.com/a/38501328
    # https://flask.palletsprojects.com/en/2.0.x/reqcontext/#notes-on-proxies

    scheduler = BackgroundScheduler(timezone=utc)
    app = current_app._get_current_object()

    # add background job that posts new videos once a day
    scheduler.add_job(
        func=process_videos,
        args=[app],
        trigger="cron",
        hour=current_app.config["CRON_HOUR"],
        id="post",
        replace_existing=True,
    )

    atexit.register(lambda: scheduler.shutdown(wait=False))
    scheduler.start()


def reindex(app):
    with app.app_context():
        Post.reindex()


def populate_search_index():
    if not current_app.index.is_empty():
        return

    app = current_app._get_current_object()
    thread = Thread(target=reindex, name="search_index", args=[app])
    thread.start()
