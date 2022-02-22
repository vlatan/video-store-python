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


def get_all_videos(api_key):
    # get all playlists from db
    playlists, all_videos = Playlist.query.all(), []
    # construct youtube API service
    with build('youtube', 'v3', developerKey=api_key,
               cache_discovery=False) as youtube:
        # loop through the playlists
        for playlist in playlists:
            # get playlist VALID videos from YT
            playlist_videos = get_playlist_videos(
                playlist.playlist_id, youtube)

            # loop through the videos in this playlist
            for video in playlist_videos:
                # add relationship with this playlist to the video metadata
                video['playlist'] = playlist
            # add this batch of videos to the total list of videos
            all_videos += playlist_videos
    return all_videos


def post_new_videos(app):
    with app.app_context():
        API_KEY = current_app.config['YOUTUBE_API_KEY']
        PER_PAGE = current_app.config['NUM_RELATED_POSTS']

    # get all VALID videos from our playlists from YouTube
    all_videos = get_all_videos(API_KEY)
    # shuffle videos so they don't get posted uniformly
    random.shuffle(all_videos)

    # loop through total number of videos
    for video in all_videos:
        with app.app_context():
            # do the work in db context menager (autocommit)
            # to ensure db is left in a healthy state if exception is raised
            # transactions commited ор rolled back and session closed
            with db.session.begin():
                # if video is already posted (by a form submit as single video)
                if (posted := Post.query.filter_by(video_id=video['video_id']).first()):
                    # if it doesn't have playlist id
                    if not posted.playlist_id:
                        # add playlist id
                        posted.playlist_id = video['playlist_id']
                        # asscoiate with existing playlist in our db
                        posted.playlist = video['playlist']
                else:
                    # search for related videos using the post title
                    if not (related_posts := Post.search(
                            video['title'], 1, PER_PAGE)[0].all()):
                        related_posts = Post.query.order_by(
                            func.random()).limit(PER_PAGE).all()
                    # create object from Model
                    post = Post(**video, related_posts=related_posts)
                    # add post to database
                    db.session.add(post)
        time.sleep(5)


def revalidate_video(post, api_key, per_page):
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
            if validate_video(res):
                # get related posts by searching the index using the title of this post
                related_posts = Post.search(
                    post.title, 1, per_page + 1)[0].all()[1:]
                # if there's change in the related posts
                if related_posts and post.related_posts != related_posts:
                    post.related_posts = related_posts
                    db.session.commit()

        # video is not validated or doesn't exist at YouTube
        except (IndexError, ValidationError):
            db.session.delete(post)
            db.session.commit()
            return
        except HttpError:
            # we couldn't connect to YouTube API,
            # so we can't evaluate the video
            pass

        # set last_checked time in the db for this post
        post.last_checked = datetime.utcnow()
        db.session.commit()


# def revalidate_existing_videos(app):
#     with app.app_context():
#         API_KEY = current_app.config['YOUTUBE_API_KEY']
#         PER_PAGE = current_app.config['NUM_RELATED_POSTS']
#         time_flag = datetime.utcnow() - timedelta(days=3)
#         posts = Post.query.filter(Post.last_checked < time_flag)
#         for post in posts:
#             revalidate_video(post, API_KEY, PER_PAGE)

def revalidate_existing_videos(app):
    with app.app_context():
        print('Started revalidating videos.')
        API_KEY = current_app.config['YOUTUBE_API_KEY']
        PER_PAGE = current_app.config['NUM_RELATED_POSTS']
        posts = Post.query.order_by(Post.id.desc()).all()
        print(posts[:10])
        part = ['status', 'snippet', 'contentDetails']

        with build('youtube', 'v3', developerKey=API_KEY, cache_discovery=False) as youtube:
            # you can get max 50 videos per call from YouTube API
            for i in range(0, len(posts), 50):
                track_posts = {post.video_id: post for post in posts[i:i+50]}
                try:
                    req = youtube.videos().list(id=list(track_posts.keys()), part=part)
                    items = req.execute()['items']
                    print(f'{len(track_posts)} items fetched from YouTube API')
                except HttpError:
                    # we couldn't connect to YouTube API,
                    # so we can't evaluate this entire chunk
                    print('Couldn\'t connect to YouTube API')
                    continue

                print('Looping through the items.')
                for item in items:
                    post = track_posts.get(item['id'])
                    print(f'Processing post {post.id}')
                    try:
                        # this will raise ValidationError if not valid
                        validate_video(item)
                        print(f'Video {post.id} is VALID.')

                        # get related posts by searching the index,
                        # using the title of this post
                        related_posts = Post.search(
                            post.title, 1, PER_PAGE + 1)[0].all()[1:]

                        if related_posts:
                            if post.related_posts != related_posts:
                                post.related_posts = related_posts
                                db.session.commit()
                                print(
                                    f'Related posts for post {post.id} updated.')
                        else:
                            post.related_posts = Post.query.order_by(
                                func.random()).limit(PER_PAGE).all()
                            db.session.commit()
                            print(
                                f'Related posts for post {post.id} updated (random).')

                        print('-' * 30)

                    except ValidationError:
                        # delete invalid video
                        db.session.delete(post)
                        db.session.commit()
                        print(f'Video {post.id} is INVALID and deleted.')
                        print('-' * 30)

                    # remove video from tracked posts
                    track_posts.pop(post.video_id)
                    time.sleep(0.5)

                if items:
                    # posts still remaining in track_posts were not
                    # present at YouTube at all, therefore delete from db
                    for post in track_posts.values():
                        db.session.delete(post)
                        db.session.commit()
                        print(f'Video {post.id} is MISSING and deleted.')
                        time.sleep(0.5)


def init_scheduler_jobs():
    # https://stackoverflow.com/a/38501328
    # https://flask.palletsprojects.com/en/0.12.x/reqcontext/#notes-on-proxies

    # add background job that posts new videos once a day
    current_app.scheduler.add_job(func=post_new_videos,
                                  args=[current_app._get_current_object()],
                                  trigger='cron', minute=49,
                                  id='post', replace_existing=True)

    # add background job that revalidates all eligible videos every two days
    # current_app.scheduler.add_job(func=revalidate_existing_videos,
    #                               args=[current_app._get_current_object()],
    #                               trigger='cron', minute=12,
    #                               id='revalidate', replace_existing=True)

    pass
