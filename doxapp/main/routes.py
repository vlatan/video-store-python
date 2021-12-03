import time
from flask import (render_template, request, redirect,
                   url_for, Blueprint, jsonify, make_response)
from doxapp.models import Post
import threading

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
def cron():
    """ Route to fetch videos from the YT chanels called.
        This view is called from CRON.
        Check basis authentication to secure this view.
        https://stackoverflow.com/a/55740595 """

    def test_function():
        print('YouTube thread started runing for 30 seconds...')
        time.sleep(30)

    if 'YouTube' not in [t.name for t in threading.enumerate()]:
        thread = threading.Thread(target=test_function, name='YouTube')
        thread.start()
    else:
        print('Previous YouTube thread is still running!')

    return redirect(url_for('main.home'))


@main.route('/about/')
def about():
    return render_template('about.html', title='About')
