import random
from flask import Blueprint, current_app
from app import db
from app.models import Post, Playlist
from app.cron.helpers import get_playlist_videos
from googleapiclient.discovery import build


cron = Blueprint('cron', __name__)


def post_new_videos(app):
    with app.app_context():
        API_KEY = current_app.config['YOUTUBE_API_KEY']
        PER_PAGE = current_app.config['NUM_RELATED_POSTS']
        # get all playlists from db
        playlists, all_videos = Playlist.query.all(), []
        # construct youtube API service
        with build('youtube', 'v3', developerKey=API_KEY) as youtube:
            # loop through the playlists
            for playlist in playlists:
                # get playlist videos from YT
                playlist_videos = get_playlist_videos(
                    playlist.playlist_id, youtube)
                # loop through the videos in this playlist
                for video in playlist_videos:
                    # add relationship with this playlist to the video metadata
                    video['playlist'] = playlist
                # add this batch of videos to the total list of videos
                all_videos += playlist_videos

        # shuffle videos so the don't get posted uniformly
        random.shuffle(all_videos)

        # loop through total number of videos
        for video in all_videos:
            # if video is already posted (via webform as a single video submit)
            if (posted := Post.query.filter_by(video_id=video['video_id']).first()):
                # if it doesn't have playlist id
                if not posted.playlist_id:
                    # add playlist id
                    posted.playlist_id = video['playlist_id']
                    # asscoiate with existing playlist in our db
                    posted.playlist = video['playlist']
                    # commit
                    db.session.commit()
            else:
                # create object from Model
                post = Post(**video)
                # search for related videos using the post title
                if (related_posts := Post.search(post.title, 1, PER_PAGE)[0].all()):
                    post.related_posts = related_posts

                # add post to database
                db.session.add(post)
                db.session.commit()


@cron.before_app_first_request
def init_scheduler():
    # https://stackoverflow.com/a/38501328
    # https://flask.palletsprojects.com/en/0.12.x/reqcontext/#notes-on-proxies

    current_app.scheduler.add_job(func=post_new_videos,
                                  args=[current_app._get_current_object()],
                                  trigger='interval', days=2)
