from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from flask import current_app
from app.helpers import dump_datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    openid = db.Column(db.String(256), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(120), nullable=False)
    picture = db.Column(db.String(256), nullable=False)
    posts = db.relationship('Post', backref='video_poster', lazy=True)
    playlists = db.relationship(
        'Playlist', backref='playlist_poster', lazy=True)

    @property
    def is_admin(self):
        admin_email = current_app.config['ADMIN_EMAIL']
        if self.email == admin_email:
            return True
        return False


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(50), unique=True, nullable=False)
    channel_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    channel_thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='playlist', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(7), default='YouTube')
    video_id = db.Column(db.String(20), unique=True, nullable=False)
    playlist_id = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.PickleType)
    duration = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    playlist_db_id = db.Column(db.Integer, db.ForeignKey(Playlist.id))

    @property
    def serialize(self):
        """ Return object data in easily serializable format. """
        return {
            'id': self.id,
            'provider': self.provider,
            'video_id': self.video_id,
            'playlist_id': self.channel_id,
            'title': self.title,
            'thumbnails': self.thumbnails,
            'description': self.description,
            'tags': self.tags,
            'duration': self.duration,
            'upload_date': dump_datetime(self.upload_date),
            'date_posted': dump_datetime(self.date_posted),
            'last_checked': dump_datetime(self.last_checked),
            'user_id': self.user_id,
            'channel_db_id': self.channel_db_id
        }
