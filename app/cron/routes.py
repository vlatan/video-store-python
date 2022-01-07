import threading
import random
from flask import url_for, Blueprint, redirect, current_app
from flask_login import login_required
from app import db
from app.models import Post, Playlist, SearchableMixin
from app.helpers import admin_required
from app.cron.helpers import get_playlist_videos
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from googleapiclient.discovery import build


cron = Blueprint('cron', __name__)


@cron.route('/pingapi')
@login_required
@admin_required
def cronjob():
    """ Route to fetch videos from the YT chanels.
        This view is called from CRON.
        Check basic authentication to secure this view.
        https://stackoverflow.com/a/55740595 """

    API_KEY = current_app.config['YOUTUBE_API_KEY']
    # number of related posts to fetch
    per_page = current_app.config['NUM_RELATED_POSTS']
    # we need the full DB uri relative to the app
    # so we can properly create the engine
    DB = current_app.config['SCOPPED_SESSION_DB_URI']
    engine = create_engine(DB)
    session_factory = sessionmaker(bind=engine)

    def post_videos():

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

    # start the post_videos() function in a thread if it's not already running
    if 'YouTube' not in [t.name for t in threading.enumerate()]:
        thread = threading.Thread(target=post_videos, name='YouTube')
        thread.start()

    # redirect to home, we're not waiting for the thread
    return redirect(url_for('main.home'))
