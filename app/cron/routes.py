import random
import atexit
from flask import Blueprint, current_app
from app import db
from app.models import Post, Playlist, SearchableMixin
from app.cron.helpers import get_playlist_videos
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler


cron = Blueprint('cron', __name__)


def post_videos(session_factory, api_key, per_page):
    # all calls to Session() will create a thread-local session
    Session = scoped_session(session_factory)
    # instantiate a session
    session = Session()

    # listen for commit and make changes to search index
    db.event.listen(session, 'before_commit',
                    SearchableMixin.before_commit)
    db.event.listen(session, 'after_commit', SearchableMixin.after_commit)

    try:
        # get all playlists from db
        playlists, all_videos = session.query(Playlist).all(), []
        # construct youtube API service
        with build('youtube', 'v3', developerKey=api_key) as youtube:
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
            if (posted := session.query(Post).filter_by(video_id=video['video_id']).first()):
                # if it doesn't have playlist id
                if not posted.playlist_id:
                    # add playlist id
                    posted.playlist_id = video['playlist_id']
                    # asscoiate with existing playlist in our db
                    posted.playlist = video['playlist']
                    # commit
                    session.commit()
            else:
                # create object from Model
                post = Post(**video)
                # search for related videos using the post title
                if (related_posts := Post.search(post.title, 1, per_page, session=session)[0].all()):
                    post.related_posts = related_posts

                # add post to database
                session.add(post)
                session.commit()
    finally:
        # lastly remove the Session no matter what
        Session.remove()


@cron.before_app_first_request
def init_scheduler():
    # https://stackoverflow.com/a/38501328

    API_KEY = current_app.config['YOUTUBE_API_KEY']
    PER_PAGE = current_app.config['NUM_RELATED_POSTS']
    DB_URI = current_app.config['SCOPPED_SESSION_DB_URI']

    engine = create_engine(DB_URI)
    session_factory = sessionmaker(bind=engine)

    scheduler = BackgroundScheduler(timezone=current_app.config['TIMEZONE'])
    scheduler.add_job(func=post_videos,
                      args=[session_factory, API_KEY, PER_PAGE],
                      trigger='interval', days=2)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
