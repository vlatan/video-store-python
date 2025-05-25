import time
import random
import functools
from typing import Any, Callable

from flask import current_app
from wtforms.validators import ValidationError
from app.posts.helpers import video_banned, validate_video, fetch_video_data


def get_playlist_videos(playlist_id: str, youtube) -> tuple[list[dict], bool]:
    # videos epmty list and first page token is None
    videos, next_page_token, complete = [], None, False

    api = YouTubeAPI(youtube)

    # iterate through all the items in the Uploads playlist
    while True:
        try:
            # scope for creating a batch of 50 from the playlist
            scope = {
                "playlistId": playlist_id,
                "part": "contentDetails",
                "maxResults": 50,
                "pageToken": next_page_token,
            }
            # every time it loops it gets the next 50 videos
            uploads = api.get_playlist_videos(scope)

            # scope for detalied info about each video in this batch
            scope = {
                "id": [item["contentDetails"]["videoId"] for item in uploads["items"]],
                "part": ["status", "snippet", "contentDetails"],
            }

            # this will raise MaxRetriesExceededError if unsuccessful
            res = api.get_videos(scope)

            # this will raise ValueError if unable to access "items"
            items = res["items"]

        except (MaxRetriesExceededError, ValueError):
            # failed to connect to YT API
            # we abandon further operation
            # because we don't have the next token
            break

        # loop through this batch of videos
        # if there are no videos res['items'] will be empty list
        for item in items:
            try:
                # this will raise ValidationError if video's invalid
                if validate_video(item) and not video_banned(item["id"]):
                    video_info = fetch_video_data(item, playlist_id=playlist_id)
                    videos.append(video_info)
            except ValidationError:
                # video not validated
                # continue, try the next video
                continue

        # update the next page token
        next_page_token = uploads.get("nextPageToken")

        # if no more pages break the while loop, we're done
        if next_page_token is None:
            complete = True
            break

    return videos, complete


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
            for _ in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    retry_delay += random.uniform(0, 1)

            current_app.logger.exception(
                f"All {max_retries} attempts failed for '{func.__name__}.\n"
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


class YouTubeAPI:
    """Provides methods to fetch various resources from the YouTube API."""

    def __init__(self, youtube_resource):
        self.youtube = youtube_resource

    @retry(max_retries=3)
    def get_videos(self, scope: dict) -> dict:
        return self.youtube.videos().list(**scope).execute()

    @retry(max_retries=3)
    def get_playlists(self, scope: dict) -> dict:
        return self.youtube.playlists().list(**scope).execute()

    @retry(max_retries=3)
    def get_channels(self, scope: dict) -> dict:
        return self.youtube.channels().list(**scope).execute()

    @retry(max_retries=3)
    def get_playlist_videos(self, scope: dict) -> dict:
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
