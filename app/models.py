from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from flask import current_app
from app.helpers import dump_datetime, add_to_index
from app.helpers import remove_from_index, query_index


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class ActionMixin(object):
    def cast(self, post, action):
        if not self.has_casted(post, action):
            model = PostLike if action == 'like' else PostFave
            cast = model(user_id=self.id, post_id=post.id)
            db.session.add(cast)

    def uncast(self, post, action):
        if self.has_casted(post, action):
            model = PostLike if action == 'like' else PostFave
            cast = model.query.filter_by(user_id=self.id, post_id=post.id)
            cast.delete()

    def has_casted(self, post, action):
        model = PostLike if action == 'like' else PostFave
        return model.query.filter(
            model.user_id == self.id,
            model.post_id == post.id).count() > 0


class User(db.Model, UserMixin, ActionMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(256), unique=True, nullable=True)
    facebook_id = db.Column(db.String(256), unique=True, nullable=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    picture = db.Column(db.String(512))
    local_picture = db.Column(db.String(120), default='default.jpg')
    posts = db.relationship('Post', backref='author', lazy=True)
    playlists = db.relationship('Playlist', backref='author', lazy=True)
    liked = db.relationship('PostLike', backref='user', lazy=True)
    faved = db.relationship('PostFave', backref='user',
                            cascade='all,delete', lazy='dynamic')

    @property
    def is_admin(self):
        admin_openid = current_app.config['ADMIN_OPENID']
        if self.google_id == admin_openid:
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class SearchableMixin(object):
    @classmethod
    def search(cls, keyword, page, per_page, session=None):
        # check if scopped session is in use
        search_query = session.query(cls) if session else cls.query
        ids, total = query_index(cls.__tablename__, keyword, page, per_page)
        if total == 0:
            return search_query.filter_by(id=0), 0
        when = [(ids[i], i) for i in range(len(ids))]
        return search_query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add'] + session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


class Post(db.Model, SearchableMixin):
    __searchable__ = ['title', 'description', 'tags']
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(7), default='YouTube')
    video_id = db.Column(db.String(20), unique=True, nullable=False)
    playlist_id = db.Column(db.String(50))
    title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.Text)
    duration = db.Column(db.String(10), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    playlist_db_id = db.Column(db.Integer, db.ForeignKey('playlist.id'))
    related_posts = db.Column(db.PickleType, default=[])
    likes = db.relationship('PostLike', backref='post',
                            cascade='all,delete', lazy='dynamic')
    faves = db.relationship('PostFave', backref='post',
                            cascade='all,delete', lazy=True)

    @property
    def serialize(self):
        """ Return object data in easily serializable format. """
        return {
            'id': self.id,
            'provider': self.provider,
            'video_id': self.video_id,
            'playlist_id': self.playlist_id,
            'title': self.title,
            'thumbnails': self.thumbnails,
            'description': self.description,
            'tags': self.tags,
            'duration': self.duration,
            'upload_date': dump_datetime(self.upload_date),
            'date_posted': dump_datetime(self.date_posted),
            'last_checked': dump_datetime(self.last_checked),
            'user_id': self.user_id,
            'playlist_db_id': self.playlist_db_id
        }


class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))


class PostFave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))


# listen for commit and make changes to search index
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)
