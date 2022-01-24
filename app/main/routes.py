import time
from flask import render_template, request, current_app
from flask import Blueprint, jsonify, make_response
from app.models import Post

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
    return render_template('content.html', posts=posts, title='Doxder')


@main.route('/about')
def about():
    return render_template('about.html', title='About')
