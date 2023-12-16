import sqlalchemy
from slugify import slugify
from markdown import markdown
from datetime import datetime

from flask_login import UserMixin
from flask import current_app, escape

from app import db, login_manager, cache
from app.helpers import add_to_index, remove_from_index, query_index


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Base(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ActionMixin(db.Model):
    __abstract__ = True

    def cast(self, post, action):
        obj = PostLike if action in ["like", "unlike"] else PostFave
        # if user hasn't liked/faved the post record her like/fave
        if not self.has_casted(post, action):
            cast = obj(user_id=self.id, post_id=post.id)
            db.session.add(cast)
        # if user already liked/faved this post delete her like/fave
        else:
            cast = obj.query.filter_by(user_id=self.id, post_id=post.id)
            cast.delete()

    def has_casted(self, post, action):
        obj = PostLike if action in ["like", "unlike"] else PostFave
        query = obj.query.filter(obj.user_id == self.id, obj.post_id == post.id)
        return query.count() > 0


class SearchableMixin(db.Model):
    __abstract__ = True

    @classmethod
    def search(cls, keyword, page, per_page):
        ids, total = query_index(cls.__searchable__, keyword, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = [(ids[i], i) for i in range(len(ids))]
        query = cls.query.filter(cls.id.in_(ids)).order_by(db.case(*when, value=cls.id))
        return query, total

    @classmethod
    def _fields_dirty(cls, obj):
        if not isinstance(obj, cls):
            return False
        insp = sqlalchemy.inspect(obj)  # https://stackoverflow.com/a/28353846
        attrs = [getattr(insp.attrs, key) for key in obj.__searchable__]
        return any([attr.history.has_changes() for attr in attrs])

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            "add": [obj for obj in session.new if isinstance(obj, cls)],
            "update": [obj for obj in session.dirty if cls._fields_dirty(obj)],
            "delete": [obj for obj in session.deleted if isinstance(obj, cls)],
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes["add"] + session._changes["update"]:
            add_to_index(obj)
        for obj in session._changes["delete"]:
            remove_from_index(obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(obj)


class User(Base, UserMixin, ActionMixin):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(2048))
    google_id = db.Column(db.String(256), unique=True, nullable=True, index=True)
    facebook_id = db.Column(db.String(256), unique=True, nullable=True, index=True)
    analytics_id = db.Column(db.String(512))
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    picture = db.Column(db.String(512))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship("Post", backref="author", lazy=True)
    playlists = db.relationship("Playlist", backref="author", lazy=True)
    liked = db.relationship(
        "PostLike", backref="user", cascade="all,delete-orphan", lazy="dynamic"
    )
    faved = db.relationship(
        "PostFave", backref="user", cascade="all,delete-orphan", lazy="dynamic"
    )

    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.google_id == current_app.config["ADMIN_OPENID"]


class Post(Base, SearchableMixin):
    __searchable__ = ["title", "description", "tags"]
    id = db.Column(db.Integer, primary_key=True, index=True)
    provider = db.Column(db.String(7), default="YouTube")
    video_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    playlist_id = db.Column(db.String(50))
    title = db.Column(db.String(256), nullable=False)
    thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.Text)
    tags = db.Column(db.Text)
    duration = db.Column(db.String(10), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)
    similar = db.Column(db.PickleType, default=[])

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    playlist_db_id = db.Column(db.Integer, db.ForeignKey("playlist.id"))

    likes = db.relationship(
        "PostLike", backref="post", cascade="all,delete-orphan", lazy="dynamic"
    )
    faves = db.relationship(
        "PostFave", backref="post", cascade="all,delete-orphan", lazy="dynamic"
    )

    def srcset(self, max_width=1280):
        """Return string of srcset images for a post."""
        thumbs = sorted(self.thumbnails.values(), key=lambda x: x["width"])
        srcset = [
            f"{item['url']} {item['width']}w"
            for item in thumbs
            if item["width"] <= max_width
        ]
        return ", ".join(srcset)

    @property
    def serialize(self):
        """Return object data in easily serializable format."""
        return {
            "id": self.id,
            "video_id": self.video_id,
            "title": escape(self.title),
            "thumbnails": self.thumbnails,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "srcset": self.srcset(max_width=480),
        }

    @classmethod
    @cache.memoize(86400)
    def get_posts(cls, page, per_page):
        query = cls.query.order_by(cls.upload_date.desc())
        posts = query.paginate(page=page, per_page=per_page, error_out=False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_posts_by_likes(cls, page, per_page):
        """
        Query posts by likes (outerjoin)
        https://stackoverflow.com/q/63889938
        """
        query = cls.query.outerjoin(PostLike).group_by(cls.id)
        query = query.order_by(sqlalchemy.func.count().desc())
        posts = query.paginate(page=page, per_page=per_page, error_out=False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_related_posts(cls, title, per_page):
        if not (posts := cls.search(title, 1, per_page + 1)[0]):
            posts = cls.query.order_by(sqlalchemy.func.random()).limit(per_page)
        return [post.serialize for post in posts if post.title != title]

    @classmethod
    @cache.memoize(86400)
    def get_playlist_posts(cls, playlist_id, page, per_page):
        query = cls.query.filter_by(playlist_id=playlist_id)
        query = query.order_by(cls.upload_date.desc())
        posts = query.paginate(page=page, per_page=per_page, error_out=False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_orphans(cls, page, per_page):
        src_ids = [pl.playlist_id for pl in Playlist.query.all()]
        orphans = (cls.playlist_id == None) | (cls.playlist_id.not_in(src_ids))
        query = cls.query.filter(orphans).order_by(cls.upload_date.desc())
        posts = query.paginate(page=page, per_page=per_page, error_out=False).items
        return [post.serialize for post in posts]

    @classmethod
    @cache.memoize(86400)
    def get_posts_by_id(cls, ids):
        if not ids:
            return ids
        when = [(ids[i], i) for i in range(len(ids))]
        posts = cls.query.filter(cls.id.in_(ids)).order_by(db.case(*when, value=cls.id))
        return [post.serialize for post in posts]


class DeletedPost(Base):
    id = db.Column(db.Integer, primary_key=True, index=True)
    provider = db.Column(db.String(7), default="YouTube")
    video_id = db.Column(db.String(20), unique=True, nullable=False, index=True)


class Page(Base):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text)
    slug = db.Column(db.String(255))

    def __init__(self, *args, **kwargs):
        if not "slug" in kwargs:
            slug = slugify(kwargs.get("title", ""), allow_unicode=True)
            kwargs["slug"] = slug
        super().__init__(*args, **kwargs)

    @cache.memoize(86400)
    def html_content(self):
        return markdown(self.content)

    def delete_cache(self):
        # https://flask-caching.readthedocs.io/en/latest/#deleting-memoize-cache
        cache.delete_memoized(self.html_content)


class Playlist(Base):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(50), unique=True, nullable=False)
    channel_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    channel_title = db.Column(db.String(256))
    thumbnails = db.Column(db.PickleType, nullable=False)
    channel_thumbnails = db.Column(db.PickleType, nullable=False)
    description = db.Column(db.Text)
    channel_description = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    posts = db.relationship("Post", backref="playlist", lazy=True)


class PostLike(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))


class PostFave(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"))


# listen for commit and make changes to search index
db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)
