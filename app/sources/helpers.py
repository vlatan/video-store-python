from urllib.parse import urlparse, parse_qs
from googleapiclient.errors import HttpError
from wtforms.validators import ValidationError

from app.cron.handlers import get_youtube_playlists, get_youtube_channels


def parse_playlist(url):
    parsed = urlparse(url)
    youtube_hostnames = ("www.youtube.com", "youtube.com", "youtu.be")
    if parsed.hostname and parsed.hostname in youtube_hostnames:
        if query := parse_qs(parsed.query).get("list"):
            return query[0]
    raise ValidationError("Unable to parse the URL.")


def validate_playlist(playlist_id, youtube):
    try:
        scope = {"id": playlist_id, "part": "snippet"}
        if not (res := get_youtube_playlists(youtube, scope)):
            raise HttpError(res, scope)

        # this will raise either ValueError or IndexError
        res = res["items"][0]

        channel_id = res["snippet"]["channelId"]
        scope = {"id": channel_id, "part": "snippet"}
        if not (ch := get_youtube_channels(youtube, scope)):
            raise HttpError(res, scope)

        # this will raise either ValueError or IndexError
        ch = ch["items"][0]

        return {
            "playlist_id": playlist_id,
            "channel_id": channel_id,
            "title": res["snippet"]["title"],
            "channel_title": ch["snippet"]["title"],
            "thumbnails": res["snippet"]["thumbnails"],
            "channel_thumbnails": ch["snippet"]["thumbnails"],
            "description": res["snippet"].get("description"),
            "channel_description": ch["snippet"].get("description"),
        }

    # could not connect to YT API (HttpError)
    # or the playlist doesn't exist (IndexError)
    except (HttpError, ValueError, IndexError):
        raise ValidationError("Unable to fetch the playlist.")
