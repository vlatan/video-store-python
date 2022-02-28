from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from flask import current_app
from app import cache
from app.helpers import add_to_index
from app.helpers import remove_from_index, query_index
from sqlalchemy import func, inspect


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Base(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class ActionMixin(object):
    def cast(self, post, action):
        obj = PostLike if action in ['like', 'unlike'] else PostFave
        # if user hasn't liked/faved the post record her like/fave
        if not self.has_casted(post, action):
            cast = obj(user_id=self.id, post_id=post.id)
            db.session.add(cast)
        # if user already liked/faved this post delete her like/fave
        else:
            cast = obj.query.filter_by(user_id=self.id, post_id=post.id)
            cast.delete()

    def has_casted(self, post, action):
        obj = PostLike if action in ['like', 'unlike'] else PostFave
        return obj.query.filter(obj.user_id == self.id,
                                obj.post_id == post.id).count() > 0


class SearchableMixin(object):
    @classmethod
    def search(cls, keyword, page, per_page):
        ids, total = query_index(cls.__tablename__, keyword, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = [(ids[i], i) for i in range(len(ids))]
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def fields_dirty(cls, obj):
        if isinstance(obj, cls):
            # https://stackoverflow.com/a/28353846
            insp = inspect(obj)
            attrs = [getattr(insp.attrs, key) for key in obj.__searchable__]
            return any([attr.history.has_changes() for attr in attrs])
        return False

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': [obj for obj in session.new if isinstance(obj, cls)],
            'update': [obj for obj in session.dirty if cls.fields_dirty(obj)],
            'delete': [obj for obj in session.deleted if isinstance(obj, cls)]
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add'] + session._changes['update']:
            add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


class User(Base, UserMixin, ActionMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(256), unique=True,
                          nullable=True, index=True)
    facebook_id = db.Column(db.String(256), unique=True,
                            nullable=True, index=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    picture = db.Column(db.String(512))
    local_picture = db.Column(db.String(120), default='default.jpg')

    posts = db.relationship('Post', backref='author', lazy=True)
    playlists = db.relationship('Playlist', backref='author', lazy=True)
    liked = db.relationship('PostLike', backref='user',
                            cascade='all,delete-orphan', lazy='dynamic')
    faved = db.relationship('PostFave', backref='user',
                            cascade='all,delete-orphan', lazy='dynamic')

    @property
    def is_admin(self):
        admin_openid = current_app.config['ADMIN_OPENID']
        if self.google_id == admin_openid:
            return True
        return False


class Post(Base, SearchableMixin):
    __searchable__ = ['title', 'description', 'tags']
    id = db.Column(db.Integer, primary_key=True, index=True)
    provider = db.Column(db.String(7), default='YouTube')
    video_id = db.Column(db.String(20), unique=True,
                         nullable=False, index=True)
    playlist_id = db.Column(db.String(50))
    title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.Text)
    duration = db.Column(db.String(10), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    playlist_db_id = db.Column(db.Integer, db.ForeignKey('playlist.id'))

    children = db.relationship(
        'Post', backref=db.backref('parent', remote_side=[id]))
    likes = db.relationship('PostLike', backref='post',
                            cascade='all,delete-orphan', lazy='dynamic')
    faves = db.relationship('PostFave', backref='post',
                            cascade='all,delete-orphan', lazy='dynamic')

    @property
    def serialize(self):
        """ Return object data in easily serializable format. """
        return {
            'video_id': self.video_id,
            'title': self.title,
            'thumbnails': self.thumbnails
        }

    @classmethod
    @cache.memoize(600)
    def get_posts(cls, page, per_page):
        query = cls.query.order_by(cls.id.desc())
        posts = query.paginate(page, per_page, False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(600)
    def get_posts_by_likes(cls, page, per_page):
        """ query posts by likes (outerjoin)
            https://stackoverflow.com/q/63889938 """

        query = cls.query.outerjoin(PostLike).group_by(
            cls.id).order_by(func.count().desc())
        posts = query.paginate(page, per_page, False).items
        return [post.serialize for post in posts]


class Playlist(Base):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(50), unique=True, nullable=False)
    channel_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    channel_thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    posts = db.relationship('Post', backref='playlist', lazy=True)


class PostLike(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))


class PostFave(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))


# listen for commit and make changes to search index
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)
