import time
import random
import functools
from pydantic import BaseModel
from typing import Callable, Any
from wtforms.validators import ValidationError
from sqlalchemy.orm.exc import ObjectDeletedError
from sqlalchemy.exc import IntegrityError, StatementError

from flask import current_app

from app import db
from app.helpers import youtube_build
from app.posts.helpers import validate_video
from app.models import Post, Playlist, Category
from app.cron.helpers import get_playlist_videos
from app.sources.helpers import validate_playlist


class Documentary(BaseModel):
    title: str = ""
    description: str = ""
    category: str = ""


def get_youtube_videos_from_playlists() -> tuple[list[dict], bool]:
    all_videos, complete = [], []
    # get all playlists from db
    playlists = Playlist.query.all()
    current_app.logger.info(f"Getting videos from {len(playlists)} YT sources...")

    # construct youtube API service
    with youtube_build() as youtube:

        # loop through the playlists
        for playlist in playlists:
            # refresh playlist thumbs
            source_info = validate_playlist(playlist.playlist_id, youtube)
            playlist.channel_thumbnails = source_info["channel_thumbnails"]
            db.session.commit()

            # get playlist VALID videos from YT
            playlist_videos, done = get_playlist_videos(playlist.playlist_id, youtube)
            # record bool value if all videos from this playlist are fetched
            complete.append(done)

            # loop through the videos in this playlist
            for video in playlist_videos:
                # add relationship with this playlist to the video metadata
                video["playlist"] = playlist
            # add this batch of videos to the total list of videos
            all_videos += playlist_videos

    # remove duplicates if any
    all_videos = list({v["video_id"]: v for v in all_videos}.values())
    # sort by upload date
    all_videos = sorted(all_videos, key=lambda d: d["upload_date"])

    return all_videos, all(complete)


def revalidate_single_video(post: Post) -> bool:
    """
    Check if the video satisfies the posting criteria.
    Delete from database if it doesn't. Return True.
    Otherwise return False.

    Parameters:
    post (Post): The post sqlalcheymy object.

    Returns:
    bool: True of deleted, otherwise False.

    """
    try:
        with youtube_build() as youtube:
            api = YouTubeAPI(youtube)

            scope = {
                "id": post.video_id,
                "part": ["status", "snippet", "contentDetails"],
            }
            # this will raise MaxRetriesExceededError if unsuccessful
            res = api.get_youtube_videos(scope)

        # this will raise ValueError or IndexError
        res = res["items"][0]

        # this will raise ValidationError if video's invalid
        validate_video(res)

    # video is not validated or doesn't exist at YouTube
    except (IndexError, ValueError, ValidationError):
        try:
            db.session.delete(post)
            db.session.commit()
            return True
        except (ObjectDeletedError, StatementError) as e:
            db.session.rollback()
            msg = f"Could not delete: {post.title.upper()}. Error: {e}"
            current_app.logger.warning(msg)
    except MaxRetriesExceededError as e:
        # we couldn't connect to YouTube API,
        # so we can't evaluate the video
        pass

    return False


def process_videos() -> None:
    # get all VALID videos from our playlists from YouTube
    all_videos, complete = get_youtube_videos_from_playlists()

    # get sources/playlists ids
    sources = [pl.playlist_id for pl in Playlist.query.all()]

    # delete missing videos if all VALID videos are fetched from YT
    count_deleted = 0
    if complete:
        fetched_ids = {video["video_id"] for video in all_videos}
        posted = Post.query.filter(Post.playlist_id.in_(sources)).all()
        posted_ids = {post.video_id for post in posted}
        to_delete_ids = Post.video_id.in_(posted_ids - fetched_ids)
        for post in Post.query.filter(to_delete_ids).all():
            if revalidate_single_video(post):  # call to YT
                count_deleted += 1

    # get all possible categories in a string
    categories = db.session.execute(db.select(Category)).scalars().all()
    categories = {category.name: category for category in categories}
    cat_prompt = ", ".join(categories).replace('"', "")
    info = Documentary(title="", description="", category="")

    count_updated, count_new = 0, 0
    for video in all_videos:  # loop through total number of videos
        # if video is NOT already posted
        if not (posted := Post.query.filter_by(video_id=video["video_id"]).first()):

            # generate description and category for the video
            try:
                info = generate_info(video["title"], cat_prompt)
            except MaxRetriesExceededError:
                info = Documentary()

            if info.description:
                video["short_description"] = info.description

            # categorize the video
            if info.category in categories:
                video["category_id"] = categories[info.category].id
                video["category"] = categories[info.category]

            # create object from Model
            post = Post(**video)
            try:
                db.session.add(post)
                db.session.commit()
                count_new += 1
            except IntegrityError:
                db.session.rollback()

            # start the loop over
            continue

        is_updated = False
        try:
            # if it doesn't match the playlist id
            if posted.playlist_id != video["playlist_id"]:
                # match playlist id
                posted.playlist_id = video["playlist_id"]
                # associate with existing playlist in our db
                posted.playlist = video["playlist"]
                is_updated = True

            # update AI generated content if missing
            if not posted.short_description or not posted.category:
                try:
                    info = generate_info(posted.title, cat_prompt)
                except MaxRetriesExceededError:
                    info = Documentary()

            if not posted.short_description and info.description:
                posted.short_description = info.description
                is_updated = True

            if not posted.category and info.category in categories:
                posted.category_id = categories[info.category].id
                posted.category = categories[info.category]
                is_updated = True
        finally:
            # If no pending changes are detected,
            # then no SQL is emitted to the database
            # https://docs.sqlalchemy.org/en/20/orm/session_basics.html#committing
            db.session.commit()
            if is_updated:
                count_updated += 1

    # get orphan videos (not attached to any source/playlist)
    orphan_posts = (Post.playlist_id == None) | (Post.playlist_id.not_in(sources))
    orphan_posts = Post.query.filter(orphan_posts).all()

    # revalidate orphan videos (not attached to any source/playlist)
    for post in orphan_posts:
        if revalidate_single_video(post):  # call to YT
            count_deleted += 1
            continue

        is_updated = False
        try:
            # update AI generated content if missing
            if not post.short_description or not post.category:
                try:
                    info = generate_info(post.title, cat_prompt)
                except MaxRetriesExceededError:
                    info = Documentary()

            if not post.short_description and info.description:
                post.short_description = info.description
                is_updated = True

            # if the video is not categorized, do it
            if not post.category and info.category in categories:
                post.category_id = categories[info.category].id
                post.category = categories[info.category]
                is_updated = True
        finally:
            db.session.commit()
            if is_updated:
                count_updated += 1

    # singular or plural
    vs = lambda num: "video" if num == 1 else "videos"

    # log the processing stats
    total_videos = len(all_videos) + len(orphan_posts)
    current_app.logger.info(f"Processed {total_videos} {vs(total_videos)}.")
    current_app.logger.info(f"Added {count_new} new {vs(count_new)}.")
    current_app.logger.info(f"Deleted {count_deleted} invalid {vs(count_deleted)}.")
    current_app.logger.info(f"Updated {count_updated} current {vs(count_updated)}.")
    current_app.logger.info("Worker job done.")
    current_app.logger.info("-" * 40)


def retry(
    _func: Callable | None = None,
    start_delay: float = 0,
    max_retries: int = 5,
) -> Callable:
    """Provide retry and error logging for an API call."""

    def decorator(func: Callable) -> Callable:

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:

            # Preemptive delay before the request starts
            if start_delay > 0:
                time.sleep(start_delay)

            retry_delay, last_exception = start_delay + 1, None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    retry_delay += random.uniform(0, 1)

            current_app.logger.exception(
                f'All {max_retries} attempts failed for "{func.__name__}".\n'
                f"Args: {args}.\n"
                f"Kwargs: {kwargs}.\n"
                f"Original Error: {last_exception}."
            )

            raise MaxRetriesExceededError(
                f"Operation '{func.__name__}' failed after {max_retries} retries.",
                original_exception=last_exception,
                func_name=func.__name__,
                func_args=args,
                func_kwargs=kwargs,
            ) from last_exception

        return wrapper

    return decorator(_func) if _func else decorator


@retry(start_delay=1)
def generate_info(title: str, categories: str) -> Documentary:
    """
    Call to Gemini API.
    Generate description and a category from a generative AI based given a title and categories.
    """
    prompt = (
        f"Write one short paragraph about: {title}."
        f'Also select a category for the documentary "{title}" '
        f"from these categories: {categories}."
    )

    generate_content = current_app.config["generate_content"]
    response = generate_content(contents=prompt)

    return (
        response.parsed if isinstance(response.parsed, Documentary) else Documentary()
    )


class YouTubeAPI:
    """Provides methods to fetch various resources from the YouTube API."""

    def __init__(self, youtube_resource):
        self.youtube = youtube_resource

    @retry(max_retries=3)
    def get_youtube_videos(self, scope: dict) -> dict:
        return self.youtube.videos().list(**scope).execute()

    @retry(max_retries=3)
    def get_youtube_playlists(self, scope: dict) -> dict:
        return self.youtube.playlists().list(**scope).execute()

    @retry(max_retries=3)
    def get_youtube_channels(self, scope: dict) -> dict:
        return self.youtube.channels().list(**scope).execute()

    @retry(max_retries=3)
    def get_youtube_playlists_videos(self, scope: dict) -> dict:
        return self.youtube.playlistItems().list(**scope).execute()


class MaxRetriesExceededError(Exception):
    """Raised when a retriable operation fails after all retries are exhausted."""

    def __init__(
        self,
        message,
        original_exception=None,
        func_name=None,
        func_args=None,
        func_kwargs=None,
    ):
        super().__init__(message)
        self.original_exception = original_exception
        self.func_name = func_name
        self.func_args = func_args
        self.func_kwargs = func_kwargs
