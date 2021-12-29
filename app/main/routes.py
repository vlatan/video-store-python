import time
import threading
import random
from googleapiclient.discovery import build
from flask import render_template, request, redirect, current_app, g
from flask import url_for, Blueprint, jsonify, make_response, session
from flask_login import login_required
from app.models import Post, Playlist
from app.main.forms import SearchForm
from app.helpers import admin_required
from app.posts.helpers import get_playlist_videos
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

main = Blueprint('main', __name__)


@main.before_app_request
def before_request():
    # before the request make this search form available sitewide
    # stored in the global flask variable g
    g.search_form = SearchForm(formdata=request.args, meta={'csrf': False})


@main.route('/')
def home():
    """ Route to return the posts """
    per_page = current_app.config['POSTS_PER_PAGE']
    # get the page number
    page = request.args.get('page', 1, type=int)
    # query the Post table in descending order
    posts = Post.query.order_by(Post.id.desc())
    posts = posts.paginate(page, per_page, False).items

    # if there are subsequent pages use JavaScript to load them in infinite scroll
    if page > 1:
        # posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    return render_template('home.html', posts=posts)


@main.route('/search', methods=['GET', 'POST'])
def search():
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']

    # if it's the first page
    if request.method == 'GET':
        # validate the form from which the request is comming
        if not g.search_form.validate():
            return redirect(url_for('main.home'))
        # get the search results
        posts, total = Post.search(g.search_form.q.data, 1, per_page)
        # save search term and the number of total posts in session
        session['search_term'], session['total'] = g.search_form.q.data, total

        # render the template
        return render_template('search.html', posts=posts, total=total)

    page = request.json.get('page')
    search_term = session['search_term']
    num_posts = session['total']

    # if we got the page, search term and the total number of posts
    if page and search_term and num_posts:
        target = page * per_page
        # if there are subsequent pages pass content to frontend
        if num_posts > target or target - num_posts <= per_page:
            # get the search results
            posts, total = Post.search(search_term, page, per_page)
            # posts as JSON object
            posts = jsonify([post.serialize for post in posts])
            # Simulate delay
            time.sleep(0.4)
            return make_response(posts, 200)

    # if there are no more pages
    return make_response(jsonify([]), 200)


@ main.route('/pingapi')
@ login_required
@ admin_required
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
            # lastly remove the Session no matter what
            Session.remove()

    # start the post_videos() function in a thread if it's not already running
    if 'YouTube' not in [t.name for t in threading.enumerate()]:
        thread = threading.Thread(target=post_videos, name='YouTube')
        thread.start()

    # redirect to home, we're not waiting for the thread
    return redirect(url_for('main.home'))


@ main.route('/about')
def about():
    return render_template('about.html', title='About')
