import time
from flask import render_template, request, Blueprint, jsonify, make_response
from doxapp.models import Post

main = Blueprint('main', __name__)


# @main.route('/')
# # @main.route('/home/')
# def home():
#     page = request.args.get('page', 1, type=int)
#     posts = Post.query.order_by(
#         Post.date_posted.desc()).paginate(page=page, per_page=10)
#     return render_template('home.html', posts=posts)

@main.route('/')
def home():
    return render_template('home.html')


@main.route('/load')
def load():
    """ Route to return the posts """
    time.sleep(0.2)  # simulate delay
    quantity = 12    # number of posts to fetch per load

    if request.args:
        # The 'counter' value sent in the query string
        counter = int(request.args.get("c"))

        # Query the Post table by descending date
        posts = Post.query.order_by(Post.date_posted.desc())
        # Get a coresponding slice of the query
        posts = posts.slice(counter, counter + quantity)
        # Serialize and jsonify the posts to be read by JavaScript
        posts = jsonify([post.serialize for post in posts])

        # print(f"Returning posts {counter} to {counter + quantity}")
        # Slice counter -> quantity from the db
        return make_response(posts, 200)


@main.route('/about/')
def about():
    return render_template('about.html', title='About')
