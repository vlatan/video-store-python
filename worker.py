import logging
from app import create_app
from app.cron.handlers import process_videos


app = create_app()
app.logger.setLevel(logging.INFO)
with app.app_context():
    process_videos()
