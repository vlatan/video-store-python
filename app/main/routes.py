import time
import threading
import random
from googleapiclient.discovery import build
from flask import render_template, request, redirect, current_app
from flask import url_for, Blueprint, jsonify, make_response
from flask_login import login_required
from app import db
from app.models import Post, Playlist, SearchableMixin
from app.helpers import admin_required
from app.posts.helpers import get_playlist_videos
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

main = Blueprint('main', __name__)


@main.route('/', methods=['GET', 'POST'])
def home():
    """ Route to return the posts """
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1
    # query the Post table in descending order
    posts = Post.query.order_by(Post.id.desc())
    posts = posts.paginate(page, per_page, False).items

    if request.method == 'POST':
        # if there are subsequent pages send posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    # render template on the first view (GET method)
    return render_template('home.html', posts=posts)


@main.route('/pingapi')
@login_required
@admin_required
def cron():
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
                    # create model object
                    post = Post(**video)
                    # add to database
                    session.add(post)
                    # must imediatelly commit otherwise `db.event.listen` isn't working
                    # therefore post won't be added to the search index
                    session.commit()
                    # search for related videos using the post title
                    # and make this post parent to them
                    for p in Post.search(post.title, 1, per_page, session=session)[0].all()[1:]:
                        p.parent_id = post.id
                    # commit
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


@main.route('/about')
def about():
    return render_template('about.html', title='About')
