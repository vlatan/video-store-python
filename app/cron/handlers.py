import time
from googleapiclient.errors import HttpError
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


def get_youtube_videos() -> tuple[list[dict], bool]:
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
    with youtube_build() as youtube:
        try:
            scope = {
                "id": post.video_id,
                "part": ["status", "snippet", "contentDetails"],
            }

            req = youtube.videos().list(**scope)
            # this will raise IndexError if ['items'] is empty list``
            # which means the video does not exist
            res = req.execute()["items"][0]

            # this will raise ValidationError if video's invalid
            validate_video(res)

        # video is not validated or doesn't exist at YouTube
        except (IndexError, ValidationError):
            try:
                db.session.delete(post)
                db.session.commit()
                return True
            except (ObjectDeletedError, StatementError) as e:
                db.session.rollback()
                msg = f"Could not delete: {post.title.upper()}. Error: {e}"
                current_app.logger.warning(msg)
        except HttpError as e:
            # we couldn't connect to YouTube API,
            # so we can't evaluate the video
            msg = f"YouTube API unavailable to revalidate: {post.title.upper()}. Error: {e}"
            current_app.logger.warning(msg)

        return False


def process_videos() -> None:
    PER_PAGE = current_app.config["NUM_RELATED_POSTS"]

    # get all VALID videos from our playlists from YouTube
    all_videos, complete = get_youtube_videos()

    # get sources/playlists ids
    sources = [pl.playlist_id for pl in Playlist.query.all()]

    # get orphan videos (not attached to any source/playlist)
    orphan_posts = (Post.playlist_id == None) | (Post.playlist_id.not_in(sources))
    orphan_posts = Post.query.filter(orphan_posts).all()

    # get all possible categories
    categories = db.session.execute(db.select(Category)).scalars().all()
    categories = {category.name: category for category in categories}
    categories_string = ", ".join(categories)
    categories_string.replace('"', "")

    # singular or plural
    vs = lambda num: "video" if num == 1 else "videos"

    # log total number of videos to proocess
    total_videos = len(all_videos) + len(orphan_posts)
    current_app.logger.info(f"Processing {total_videos} {vs(total_videos)}...")

    count_updated, count_new, count_deleted = 0, 0, 0
    for video in all_videos:  # loop through total number of videos
        # if video is NOT already posted
        if not (posted := Post.query.filter_by(video_id=video["video_id"]).first()):
            # generate short description
            if short_desc := generate_description(video["title"], delay=1):
                video["short_description"] = short_desc

            # categorize the video
            category = categorize(video["title"], categories_string, delay=1)
            if category in categories:
                video["category_id"] = categories[category].id
                video["category"] = categories[category]

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

            # update similar_ids if there's a change
            similar = Post.get_related_posts(posted.title, PER_PAGE)
            if video_ids := [row["video_id"] for row in similar]:
                when = [(value, i) for i, value in enumerate(video_ids)]
                similar = (
                    Post.query.filter(Post.video_id.in_(video_ids))
                    .order_by(db.case(*when, value=Post.video_id))
                    .limit(PER_PAGE)
                    .all()
                )
                similar = [row.id for row in similar]
                if posted.similar != similar:
                    posted.similar = similar
                    is_updated = True

            # if there is NO short description in DB generate one
            if not posted.short_description:
                if short_desc := generate_description(posted.title, delay=1):
                    posted.short_description = short_desc
                    is_updated = True

            # if the video is not categorized, do it
            if not posted.category:
                category = categorize(posted.title, categories_string, delay=1)
                if category in categories:
                    posted.category_id = categories[category].id
                    posted.category = categories[category]
                    is_updated = True
        finally:
            # If no pending changes are detected,
            # then no SQL is emitted to the database
            # https://docs.sqlalchemy.org/en/20/orm/session_basics.html#committing
            db.session.commit()
            if is_updated:
                count_updated += 1

    # delete missing videos if all VALID videos are fetched from YT
    if complete:
        fetched_ids = {video["video_id"] for video in all_videos}
        posted = Post.query.filter(Post.playlist_id.in_(sources)).all()
        posted_ids = {post.video_id for post in posted}
        to_delete_ids = Post.video_id.in_(posted_ids - fetched_ids)
        for post in Post.query.filter(to_delete_ids).all():
            if revalidate_single_video(post):  # call to YT
                count_deleted += 1

    # revalidate orphan videos (not attached to any source/playlist)
    for post in orphan_posts:
        if revalidate_single_video(post):  # call to YT
            count_deleted += 1
            continue

        is_updated = False
        try:
            # if there is NO short description in DB generate one
            if not post.short_description:
                if short_desc := generate_description(post.title, delay=1):
                    post.short_description = short_desc
                    is_updated = True

            # if the video is not categorized, do it
            if not post.category:
                category = categorize(post.title, categories_string, delay=1)
                if category in categories:
                    post.category_id = categories[category].id
                    post.category = categories[category]
                    is_updated = True
        finally:
            db.session.commit()
            if is_updated:
                count_updated += 1

    # Log how many videos are edited/added
    current_app.logger.info(f"Updated {count_updated} current {vs(count_updated)}.")
    current_app.logger.info(f"Added {count_new} new {vs(count_new)}.")
    current_app.logger.info(f"Deleted {count_deleted} invalid {vs(count_deleted)}.")
    current_app.logger.info("Worker job done.")


def generate_description(title: str, delay: float) -> str | None:
    """
    Call to Gemini API.
    Generate description from a generative AI given a title.
    """

    generate_content = current_app.config["generate_content"]
    prompt = f"Write one short paragraph about: {title}."

    try:
        return generate_content(prompt).text
    except Exception as e:
        msg = f"Was unable to generate a summary for: {title.upper()}. Error: {e}"
        current_app.logger.warning(msg)

    time.sleep(delay)


def categorize(title: str, categories: str, delay: float) -> str | None:
    """
    Call to Gemini API.
    Generate a category from a generative AI based given a title and categories.
    """

    generate_content = current_app.config["generate_content"]
    prompt = f'Select a category for the documentary "{title}" from these categories: {categories}.'

    try:
        return generate_content(prompt).text
    except Exception as e:
        msg = f"Was unable to generate a category for: {title.upper()}. Error: {e}"
        current_app.logger.warning(msg)

    time.sleep(delay)
