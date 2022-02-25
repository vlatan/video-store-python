import time
import random
from datetime import datetime
from flask import current_app, Blueprint
from wtforms.validators import ValidationError
from app import db
from app.models import Post, Playlist
from app.cron.helpers import get_playlist_videos
from app.posts.helpers import validate_video
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import func

cron = Blueprint('cron', __name__)


def get_youtube_videos(api_key):
    all_videos, complete = [], True
    # get all playlists from db
    playlists = Playlist.query.all()
    # construct youtube API service
    with build('youtube', 'v3', developerKey=api_key,
               cache_discovery=False) as youtube:
        # loop through the playlists
        for playlist in playlists:
            # get playlist VALID videos from YT
            playlist_videos, done = get_playlist_videos(
                playlist.playlist_id, youtube)
            if not done:
                complete = False
            # loop through the videos in this playlist
            for video in playlist_videos:
                # add relationship with this playlist to the video metadata
                video['playlist'] = playlist
            # add this batch of videos to the total list of videos
            all_videos += playlist_videos
    return all_videos, complete


def update_related_posts(post, per_page):
    # get related posts by searching the index,
    # using the title of this post
    if related_posts := (Post.search(post.title, 1, per_page + 1)[0].all()[1:]):
        if post.related_posts != related_posts:
            post.related_posts = related_posts
    else:
        post.related_posts = Post.query.order_by(
            func.random()).limit(per_page).all()


def get_related_posts(title, per_page):
    # search for related videos using the post title
    if not (related_posts := Post.search(title, 1, per_page)[0].all()):
        # if no related get random
        related_posts = Post.query.order_by(
            func.random()).limit(per_page).all()
    return related_posts


def revalidate_single_video(post, api_key, per_page):
    with build('youtube', 'v3', developerKey=api_key,
               cache_discovery=False) as youtube:
        try:
            scope = {'id': post.video_id,
                     'part': ['status', 'snippet', 'contentDetails']}
            req = youtube.videos().list(**scope)
            # this will raise IndexError if ['items'] is empty list``
            # which means the video does not exist
            res = req.execute()['items'][0]
            # this will raise ValidationError if video's invalid
            validate_video(res)
            update_related_posts(post, per_page)
            db.session.commit()
        # video is not validated or doesn't exist at YouTube
        except (IndexError, ValidationError):
            db.session.delete(post)
            db.session.commit()
        except HttpError:
            # we couldn't connect to YouTube API,
            # so we can't evaluate the video
            pass


def process_videos(app):
    with app.app_context():
        API_KEY = current_app.config['YOUTUBE_API_KEY']
        PER_PAGE = current_app.config['NUM_RELATED_POSTS']
        # get all VALID videos from our playlists from YouTube
        all_videos, complete = get_youtube_videos(API_KEY)

    # shuffle videos so they don't get posted uniformly
    random.shuffle(all_videos)

    # loop through total number of videos
    for video in all_videos:
        with app.app_context():
            # if video is already posted
            if (posted := Post.query.filter_by(video_id=video['video_id']).first()):
                # if it doesn't have playlist id
                if not posted.playlist_id:
                    # add playlist id
                    posted.playlist_id = video['playlist_id']
                    # asscoiate with existing playlist in our db
                    posted.playlist = video['playlist']
                update_related_posts(posted, PER_PAGE)
                db.session.commit()
            else:
                related_posts = get_related_posts(video['title'], PER_PAGE)
                # create object from Model
                post = Post(**video, related_posts=related_posts)
                # add post to database
                db.session.add(post)
                db.session.commit()
        time.sleep(5)

    # delete missing videos if all VALID videos are fetched from YT
    if complete:
        fetched_ids = {video['video_id'] for video in all_videos}
        with app.app_context():
            posted = Post.query.filter(Post.playlist_id != None).all()
        posted_ids = {post.video_id for post in posted}
        with app.app_context():
            to_delete = Post.query.filter(
                Post.video_id.in_(posted_ids - fetched_ids)).all()
        for post in to_delete:
            with app.app_context():
                db.session.delete(post)
                db.session.commit()
            time.sleep(5)

    # revalidate orphan videos (not attached to playlist)
    with app.app_context():
        orphan_posts = Post.query.filter_by(playlist_id=None).all()
    for post in orphan_posts:
        with app.app_context():
            revalidate_single_video(post, API_KEY, PER_PAGE)
        time.sleep(5)


def init_scheduler_jobs():
    # https://stackoverflow.com/a/38501328
    # https://flask.palletsprojects.com/en/0.12.x/reqcontext/#notes-on-proxies

    # add background job that posts new videos once a day
    # current_app.scheduler.add_job(func=process_videos,
    #                               args=[current_app._get_current_object()],
    #                               trigger='cron', minute=3,
    #                               id='post', replace_existing=True)
    pass
