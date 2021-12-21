import time
from googleapiclient.discovery import build
from flask import render_template, request, redirect, current_app
from flask import url_for, Blueprint, jsonify, make_response
from flask_login import login_required
from app.models import Post, Playlist
from app.helpers import admin_required
from app.posts.helpers import get_playlist_videos
import threading
import random

# for setting up a scoped_session so we can query the DB in a thread
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

main = Blueprint('main', __name__)


@main.route('/')
def home():
    """ Route to return the posts """

    quantity = 12    # number of posts to fetch per load
    # Query the Post table by descending date
    posts = Post.query.order_by(Post.id.desc())

    # If there's a counter in the query string in the request
    if (counter := request.args.get("c")):
        # Convert that to integer
        counter = int(counter)
        # Get a coresponding slice of the posts query
        posts = posts.slice(counter, counter + quantity)
        # Serialize and jsonify the posts to be read by JavaScript
        posts = jsonify([post.serialize for post in posts])

        time.sleep(0.4)     # Simulate delay
        return make_response(posts, 200)

    # Get posts for the first load
    posts = posts.limit(quantity)

    return render_template('home.html', posts=posts, quantity=quantity)


@main.route('/pingapi')
@login_required
@admin_required
def cron():
    """ Route to fetch videos from the YT chanels.
        This view is called from CRON.
        Check basic authentication to secure this view.
        https://stackoverflow.com/a/55740595 """

    API_KEY = current_app.config['YOUTUBE_API_KEY']
    # we need the full DB uri relative to the app
    # so we can properly create the engine
    DB = current_app.config['SCOPPED_SESSION_DB_URI']
    engine = create_engine(DB)
    session_factory = sessionmaker(bind=engine)

    def post_videos():

        # all calls to Session() will create a thread-local session
        Session = scoped_session(session_factory)
        # create a session
        session = Session()

        try:
            # get all playlists from db
            playlists, all_videos = session.query(Playlist).all(), []
            # construct youtube API service
            with build('youtube', 'v3', developerKey=API_KEY) as youtube:
                # loop through the playlists
                for playlist in playlists:
                    # get playlist videos from YT
                    playlist_videos = get_playlist_videos(
                        playlist.playlist_id, youtube, session=session)
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
                # if video is already posted
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
                    # create model object
                    post = Post(**video)
                    # add to database
                    session.add(post)
                    # commit
                    session.commit()
        finally:
            # you must remove the Session when you're finished!
            Session.remove()

    # start the post_videos() function in a thread if it's not already running
    if 'YouTube' not in [t.name for t in threading.enumerate()]:
        thread = threading.Thread(target=post_videos, name='YouTube')
        thread.start()

    # redirect to home, we're not waiting for the thread
    return redirect(url_for('main.home'))


@main.route('/about')
def about():
    return render_template('about.html', title='About')
