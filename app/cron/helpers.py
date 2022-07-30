from app.posts.helpers import video_banned, validate_video, fetch_video_data
from wtforms.validators import ValidationError
from googleapiclient.errors import HttpError


def get_playlist_videos(playlist_id, youtube):
    # videos epmty list and first page token is None
    videos, next_page_token, complete = [], None, False

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
            uploads = youtube.playlistItems().list(**scope).execute()

            # scope for detalied info about each video in this batch
            scope = {
                "id": [item["contentDetails"]["videoId"] for item in uploads["items"]],
                "part": ["status", "snippet", "contentDetails"],
            }
            # response from YouTube
            res = youtube.videos().list(**scope).execute()
        except HttpError:
            # failed to connect to YT API
            # we abandon further operation
            # because we don't have the next token
            break

        # loop through this batch of videos
        # if there are no videos res['items'] will be empty list
        for item in res["items"]:
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
