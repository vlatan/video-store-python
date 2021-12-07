import time
from googleapiclient.discovery import build
from flask import render_template, request, redirect, current_app
from flask import url_for, Blueprint, jsonify, make_response
from flask_login import login_required
from app.models import Post, Channel
from app.utils import admin_required
from app.posts.utils import get_playlist_videos
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

    # If there's a query string in the request
    if request.args.get("c"):
        # Get the 'counter' value sent in the query string
        counter = int(request.args.get("c"))
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
        print('Querying channels...')
        channels = session.query(Channel).all()
        videos = []
        print('Constructing YouTube API service...')
        # construct youtube API service
        with build('youtube', 'v3', developerKey=API_KEY) as youtube:
            print('Constructed YouTube API service...')
            print('Going through the channels...')
            for ch in channels:
                print(f'Processing a channel... {ch.title}')
                videos += get_playlist_videos(ch.uploads_id,
                                              youtube, session=session)
                print(f'Channel "{ch.title}" processed...')
        print(f'Fetched {len(videos)} in total...')
        random.shuffle(videos)
        print('Videos shuffled...')
        print('Going through the videos...')
        for video in videos:
            post = Post(**video)
            # add post to db
            session.add(post)
            print(f'Video "{post.title}" added to DB...')
        # commit changes to DB
        session.commit()
        print('Changes to DB commited...')
        # you must close the Session when you're finished!
        Session.remove()
        print('Done...')

    if 'YouTube' not in [t.name for t in threading.enumerate()]:
        thread = threading.Thread(target=post_videos, name='YouTube')
        thread.start()

    return redirect(url_for('main.home'))


@main.route('/about/')
def about():
    return render_template('about.html', title='About')
