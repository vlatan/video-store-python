import time
from doxapp import db
from flask import (render_template, request, redirect,
                   url_for, Blueprint, jsonify, make_response)
from flask_login import login_required
from doxapp.models import Post, Channel
from doxapp.utils import admin_required
from doxapp.posts.utils import get_channel_videos
import threading
import random

main = Blueprint('main', __name__)


@main.route('/')
def home():
    """ Route to return the posts """

    quantity = 12    # number of posts to fetch per load
    # Query the Post table by descending date
    posts = Post.query.order_by(Post.date_posted.desc())

    # If there's a query string in the request
    if request.args.get("c"):
        # Get the 'counter' value sent in the query string
        counter = int(request.args.get("c"))
        # Get a coresponding slice of the query
        posts = posts.slice(counter, counter + quantity)
        # Serialize and jsonify the posts to be read by JavaScript
        posts = jsonify([post.serialize for post in posts])

        time.sleep(0.2)     # Simulate delay

        # print(f"Returning posts {counter} to {counter + quantity}")
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

    def post_videos():
        channels, videos = Channel.query.all(), []
        for ch in channels:
            videos += get_channel_videos(ch.uploads_id)
            time.sleep(20)
        random.shuffle(videos)
        for video in videos:
            post = Post(**video)
            # add to db
            db.session.add(post)
            db.session.commit()

    if 'YouTube' not in [t.name for t in threading.enumerate()]:
        thread = threading.Thread(target=post_videos, name='YouTube')
        thread.start()

    return redirect(url_for('main.home'))


@main.route('/about/')
def about():
    return render_template('about.html', title='About')
