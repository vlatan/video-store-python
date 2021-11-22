import time
from flask import render_template, request, Blueprint, jsonify, make_response
from doxapp.models import Post

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


@main.route('/about/')
def about():
    return render_template('about.html', title='About')
