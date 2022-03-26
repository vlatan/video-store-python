from collections import OrderedDict
from markdown import markdown
from slugify import slugify
from sqlalchemy import func, inspect
from datetime import datetime
from flask import current_app, escape, url_for
from flask_login import UserMixin
from app import db, login_manager, cache
from app.helpers import add_to_index, remove_from_index, query_index


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
        ids, total = query_index(cls.__searchable__, keyword, page, per_page)
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
            add_to_index(obj)
        for obj in session._changes['delete']:
            remove_from_index(obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(obj)


class SitemapMixin(object):
    @classmethod
    @cache.memoize(86400)
    def get_index(cls, order_by='id'):
        per_page = current_app.config['POSTS_PER_PAGE'] * 2
        data = OrderedDict()
        def key(x): return x.upload_date

        query, i = cls.query.order_by(getattr(cls, order_by)), 1

        while True:
            pagination = query.paginate(i, per_page, False)
            url = url_for('main.sitemap_page', what=cls.__tablename__,
                          page=i, _external=True)
            if hasattr(cls, 'posts'):
                lastmods = []
                for item in pagination.items:
                    if (freshest := max(item.posts, key=key, default=None)):
                        lastmods.append(freshest.created_at)
                if lastmods:
                    data[url] = max(lastmods).strftime('%Y-%m-%d')
            else:
                dates = [obj.updated_at for obj in pagination.items]
                if (lastmod := max(dates, default=None)):
                    data[url] = lastmod.strftime('%Y-%m-%d')
            if not pagination.has_next:
                break

            i += 1

        return data

    @classmethod
    @cache.memoize(86400)
    def get_sitemap_page(cls, page, order_by='id'):
        per_page = current_app.config['POSTS_PER_PAGE'] * 2
        data = OrderedDict()
        def key(x): return x.upload_date

        objects = cls.query.order_by(getattr(cls, order_by))
        objects = objects.paginate(page, per_page, False).items

        for obj in objects:
            if hasattr(obj, 'video_id'):
                url = url_for(
                    'posts.post', video_id=obj.video_id, _external=True)
                data[url] = obj.updated_at.strftime('%Y-%m-%d')
            elif hasattr(obj, 'playlist_id'):
                url = url_for('lists.playlist_videos',
                              playlist_id=obj.playlist_id, _external=True)
                if (last_post := max(obj.posts, key=key, default=None)):
                    data[url] = last_post.created_at.strftime('%Y-%m-%d')
            else:
                url = url_for('pages.page', slug=obj.slug, _external=True)
                data[url] = obj.updated_at.strftime('%Y-%m-%d')

        return data


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


class Post(Base, SearchableMixin, SitemapMixin):
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
    similar = db.Column(db.PickleType, default=[])

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    playlist_db_id = db.Column(db.Integer, db.ForeignKey('playlist.id'))

    likes = db.relationship('PostLike', backref='post',
                            cascade='all,delete-orphan', lazy='dynamic')
    faves = db.relationship('PostFave', backref='post',
                            cascade='all,delete-orphan', lazy='dynamic')

    @property
    def serialize(self):
        """ Return object data in easily serializable format. """
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': escape(self.title),
            'thumbnails': self.thumbnails
        }

    @classmethod
    @cache.memoize(86400)
    def get_posts(cls, page, per_page):
        query = cls.query.order_by(cls.upload_date.desc())
        posts = query.paginate(page, per_page, False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_posts_by_likes(cls, page, per_page):
        """ query posts by likes (outerjoin)
            https://stackoverflow.com/q/63889938 """

        query = cls.query.outerjoin(PostLike).group_by(
            cls.id).order_by(func.count().desc())
        posts = query.paginate(page, per_page, False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_related_posts(cls, title, per_page):
        if not (posts := cls.search(title, 1, per_page + 1)[0].all()[1:]):
            posts = cls.query.order_by(func.random()).limit(per_page).all()
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_playlist_posts(cls, playlist_id, page, per_page):
        query = cls.query.filter_by(
            playlist_id=playlist_id).order_by(cls.upload_date.desc())
        posts = query.paginate(page, per_page, False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_orphans(cls, page, per_page):
        src_ids = [pl.playlist_id for pl in Playlist.query.all()]
        orphans = (cls.playlist_id == None) | (cls.playlist_id.not_in(src_ids))
        query = cls.query.filter(orphans).order_by(cls.upload_date.desc())
        posts = query.paginate(page, per_page, False).items
        return [post.serialize for post in posts]


class Page(Base, SitemapMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text)
    slug = db.Column(db.String(255))

    def __init__(self, *args, **kwargs):
        if not 'slug' in kwargs:
            kwargs['slug'] = slugify(kwargs.get(
                'title', ''), allow_unicode=True)
        super().__init__(*args, **kwargs)

    @cache.memoize(86400)
    def html_content(self):
        return markdown(self.content)

    def delete_cache(self):
        # https://flask-caching.readthedocs.io/en/latest/#deleting-memoize-cache
        cache.delete_memoized(self.html_content)


class Playlist(Base, SitemapMixin):
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
