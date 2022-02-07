import os
import time
from flask import render_template, request, current_app
from flask import Blueprint, jsonify, make_response
from app.models import Post, PostLike
from sqlalchemy import func

main = Blueprint('main', __name__)


# autoversion css/js files
@main.app_template_filter('autoversion')
def autoversion_filter(filename):
    fullpath = os.path.join('app/', filename[1:])
    try:
        timestamp = os.path.getmtime(fullpath)
    except OSError:
        return filename
    return f'{filename}?v={timestamp}'


@main.route('/', methods=['GET', 'POST'])
def home():
    """ Route to return the posts """
    # posts per page
    per_page = current_app.config['POSTS_PER_PAGE']
    # if it's POST request this should contain data
    frontend_data = request.get_json()
    # if frontend_data get page number, else 1
    page = frontend_data.get('page') if frontend_data else 1

    if request.args.get('order_by') == 'likes':
        # query posts by likes (outerjoin)
        # https://stackoverflow.com/q/63889938
        posts_query = Post.query.outerjoin(PostLike).group_by(
            Post.id).order_by(func.count().desc())
    else:
        # query posts in descending order
        posts_query = Post.query.order_by(Post.id.desc())

    posts = posts_query.paginate(page, per_page, False).items

    if request.method == 'POST':
        # if there are subsequent pages send posts as JSON object
        posts = jsonify([post.serialize for post in posts])
        # Simulate delay
        time.sleep(0.4)
        return make_response(posts, 200)

    total = posts_query.count()
    # render template on the first view (GET method)
    return render_template('content.html', posts=posts,
                           total=total)


@main.route('/about')
def about():
    return render_template('about.html', title='About')
