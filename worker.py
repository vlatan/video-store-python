from app import create_app
from app.models import Post
from app.cron.handlers import process_videos

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        process_videos()
        Post.reindex()
