from datetime import datetime
from doxapp import db, login_manager
from flask_login import UserMixin
from doxapp.utils import dump_datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    openid = db.Column(db.String(256), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(120), nullable=False)
    picture = db.Column(db.String(256), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    # def __repr__(self):
    #     return f"User('{self.username}', '{self.email}', {self.image_file})"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(7), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    # chanel_id = db.Column(db.String(30), nullable=False)
    user_title = db.Column(db.String(256))
    provider_title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False,
                            default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), default=0)

    @property
    def serialize(self):
        """ Return object data in easily serializable format. """
        return {
            'id': self.id,
            'provider': self.provider,
            'video_id': self.video_id,
            'user_title': self.user_title,
            'provider_title': self.provider_title,
            'thumbnails': self.thumbnails,
            'upload_date': dump_datetime(self.upload_date),
            'date_posted': dump_datetime(self.date_posted),
            'user_id': self.user_id
        }

    # def __repr__(self):
    #     return f"Post('{self.title}', '{self.date_posted}')"
