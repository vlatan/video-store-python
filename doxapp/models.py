from datetime import datetime
from doxapp import db, login_manager
from flask_login import UserMixin


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
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False,
                            default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)

    # def __repr__(self):
    #     return f"Post('{self.title}', '{self.date_posted}')"
