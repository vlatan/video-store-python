from app import create_app
from celery.schedules import crontab
from app.cron.handlers import process_videos


flask_app = create_app()
celery_app = flask_app.extensions["celery"]


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute="*/6"),
        process_videos,
    )
