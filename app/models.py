import string
import sqlalchemy
from slugify import slugify
from markdown import markdown
from datetime import datetime
from markupsafe import escape
from sqlalchemy.orm import mapped_column
from redis.commands.search.query import Query
from redis.commands.search.result import Result

from flask_login import UserMixin
from flask import current_app, json

from app import db, login_manager, cache


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Base(db.Model):
    __abstract__ = True

    created_at = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at = mapped_column(
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

    def add_to_index(self):
        """Add item to Redis search index."""
        # get search index object
        search_index = current_app.config["SEARCH_INDEX"]
        # searchable fields
        searchable = {field: str(getattr(self, field)) for field in self.__searchable__}

        # additional fields
        additional = {
            "video_id": str(self.video_id),
            "thumbnail": json.dumps(self.thumbnails["medium"]),
            "srcset": str(self.srcset(max_width=480)),
        }

        # final document
        document = {**searchable, **additional}
        # add document to search
        search_index.add_document(doc_id=str(self.id), replace=True, **document)

    def remove_from_index(self):
        search_index = current_app.config["SEARCH_INDEX"]
        search_index.delete_document(str(self.id), delete_actual_document=True)

    @classmethod
    def search(cls, phrase: str, page: int, per_page: int) -> Result:
        """
        Search the RedisSearch index and return a result given the
        `phrase` and offeset and limit where offeset is `page * per_page`
        and the limit is `per_page`s.

        Parameters:
        phrase (str): Phrase to search for in the index.
        page (int): The search results page number.
        per_page (int): Number of search results per page.

        Returns:
        Result: RedisSearch Result object.
        """

        # get RedisSearch search index
        search_index = current_app.config["SEARCH_INDEX"]
        # remove punctuation from phrase
        words = phrase.translate(str.maketrans("", "", string.punctuation))
        # divide words with pipe symbol (designating OR)
        words = " | ".join(words.split())
        # make query object with offset and number of documents
        query = (
            Query(words)
            .paging(offset=page * per_page, num=per_page)
            .limit_fields(*cls.__searchable__)
        )
        # return RediSearch search result
        return search_index.search(query)

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
            obj.add_to_index()
        for obj in session._changes["delete"]:
            obj.remove_from_index()
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            obj.add_to_index()


class User(Base, UserMixin, ActionMixin):
    id = mapped_column(db.Integer, primary_key=True)
    token = mapped_column(db.String(2048))
    google_id = mapped_column(db.String(256), unique=True, nullable=True, index=True)
    facebook_id = mapped_column(db.String(256), unique=True, nullable=True, index=True)
    analytics_id = mapped_column(db.String(512))
    name = mapped_column(db.String(120))
    email = mapped_column(db.String(120))
    picture = mapped_column(db.String(512))
    last_seen = mapped_column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship("Post", backref="author", lazy=True)
    playlists = db.relationship("Playlist", backref="author", lazy=True)

    liked = db.relationship(
        "PostLike",
        backref="user",
        cascade="all,delete-orphan",
        lazy="dynamic",
    )

    faved = db.relationship(
        "PostFave",
        backref="user",
        cascade="all,delete-orphan",
        lazy="dynamic",
    )

    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.google_id == current_app.config["ADMIN_OPENID"]


class Post(Base, SearchableMixin):
    __searchable__ = ["title", "short_description", "tags"]

    id = mapped_column(db.Integer, primary_key=True)
    provider = mapped_column(db.String(7), default="YouTube")
    video_id = mapped_column(db.String(20), unique=True, nullable=False, index=True)
    playlist_id = mapped_column(db.String(50))
    title = mapped_column(db.String(256), nullable=False)
    thumbnails = mapped_column(db.PickleType, nullable=False)
    description = mapped_column(db.Text)
    short_description = mapped_column(db.Text)
    tags = mapped_column(db.Text)
    duration = mapped_column(db.String(20), nullable=False)
    upload_date = mapped_column(db.DateTime, nullable=False)
    similar = mapped_column(db.PickleType, default=[])

    user_id = mapped_column(db.Integer, db.ForeignKey("user.id"))
    category_id = mapped_column(db.Integer, db.ForeignKey("category.id"))
    playlist_db_id = mapped_column(db.Integer, db.ForeignKey("playlist.id"))

    likes = db.relationship(
        "PostLike",
        backref="post",
        cascade="all,delete-orphan",
        lazy="dynamic",
    )

    faves = db.relationship(
        "PostFave",
        backref="post",
        cascade="all,delete-orphan",
        lazy="dynamic",
    )

    @cache.memoize(86400)
    def html_content(self, text):
        return markdown(text)

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
            "video_id": self.video_id,
            "title": escape(self.title),
            "thumbnail": self.thumbnails["medium"],
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
    def get_related_posts(cls, title: str, per_page: int):
        search_result = cls.search(title, 0, per_page + 1)
        search_result = [
            {
                "video_id": doc.video_id,
                "title": escape(doc.title),
                "thumbnail": json.loads(doc.thumbnail),
                "srcset": doc.srcset,
            }
            for doc in search_result.docs
            if doc.title.lower() != title.lower()
        ]

        if len(search_result) < per_page:
            limit = per_page - len(search_result)
            posts = cls.query.order_by(sqlalchemy.func.random()).limit(limit)
            posts = [p.serialize for p in posts if p.title.lower() != title.lower()]
            search_result += posts

        return search_result

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
    def search_posts(
        cls, phrase: str, page: int, per_page: int
    ) -> tuple[list[dict[str, str]], int]:
        """Make search results ready."""

        # get search results
        search_result = cls.search(phrase, page, per_page)

        # prepare results
        docs = [
            {
                "video_id": doc.video_id,
                "title": escape(doc.title),
                "thumbnail": json.loads(doc.thumbnail),
                "srcset": doc.srcset,
            }
            for doc in search_result.docs
        ]

        return docs, search_result.total

    @classmethod
    @cache.memoize(86400)
    def get_posts_by_id(cls, ids):
        if not ids:
            return ids
        when = [(value, i) for i, value in enumerate(ids)]
        posts = cls.query.filter(cls.id.in_(ids)).order_by(db.case(*when, value=cls.id))
        return [post.serialize for post in posts]


class Category(Base):
    id = mapped_column(db.Integer, primary_key=True)
    name = mapped_column(db.String(256), unique=True, nullable=False)
    slug = mapped_column(db.String(255), unique=True, nullable=False)
    posts = db.relationship("Post", backref="category", lazy="dynamic")

    def __init__(self, *args, **kwargs):
        if not "slug" in kwargs:
            kwargs["slug"] = slugify(kwargs.get("name", ""), allow_unicode=True)
        super().__init__(*args, **kwargs)

    @cache.memoize(86400)
    def get_posts(self, page=1, per_page=24):
        posts = self.posts.order_by(Post.upload_date.desc())
        posts = posts.paginate(page=page, per_page=per_page, error_out=False)
        return [post.serialize for post in posts.items]


class DeletedPost(Base):
    id = mapped_column(db.Integer, primary_key=True)
    provider = mapped_column(db.String(7), default="YouTube")
    video_id = mapped_column(db.String(20), unique=True, nullable=False, index=True)


class Page(Base):
    id = mapped_column(db.Integer, primary_key=True)
    title = mapped_column(db.String(256), nullable=False)
    slug = mapped_column(db.String(255), unique=True, nullable=False)
    content = mapped_column(db.Text)

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
    id = mapped_column(db.Integer, primary_key=True)
    playlist_id = mapped_column(db.String(50), unique=True, nullable=False)
    channel_id = mapped_column(db.String(50), unique=True, nullable=False)
    title = mapped_column(db.String(256), nullable=False)
    channel_title = mapped_column(db.String(256))
    thumbnails = mapped_column(db.PickleType, nullable=False)
    channel_thumbnails = mapped_column(db.PickleType, nullable=False)
    description = mapped_column(db.Text)
    channel_description = mapped_column(db.Text)

    user_id = mapped_column(db.Integer, db.ForeignKey("user.id"))
    posts = db.relationship("Post", backref="playlist", lazy=True)


class PostLike(Base):
    id = mapped_column(db.Integer, primary_key=True)
    user_id = mapped_column(db.Integer, db.ForeignKey("user.id"))
    post_id = mapped_column(db.Integer, db.ForeignKey("post.id"))


class PostFave(Base):
    id = mapped_column(db.Integer, primary_key=True)
    user_id = mapped_column(db.Integer, db.ForeignKey("user.id"))
    post_id = mapped_column(db.Integer, db.ForeignKey("post.id"))


# listen for commit and make changes to search index
db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)
