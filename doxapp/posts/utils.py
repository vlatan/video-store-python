import re
import json
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from flask import current_app
from wtforms.validators import ValidationError
from doxapp.models import Post, Channel


def get_video_info(video_id, youtube):
    try:
        # if video is already posted
        if Post.query.filter_by(video_id=video_id).first():
            raise ValidationError('Video already posted')

        # the scope
        part = ['status', 'snippet', 'contentDetails']
        # construct the request for YouTube
        req = youtube.videos().list(id=video_id, part=part)
        # call YouTube API, get response (execute request)
        res = req.execute()['items'][0]

        # if video is not public
        if res['status']['privacyStatus'] != 'public':
            raise ValidationError('Video is not public.')
        # if video is not embeddable (boolean value)
        if not res['status']['embeddable']:
            raise ValidationError('Video is not embeddable.')
        # if video is geo-restricted (None if no region restrictions)
        if res['contentDetails'].get('regionRestriction'):
            raise ValidationError('Video is region restricted')
        # duration of the video
        duration = convert_video_duration(res['contentDetails']['duration'])
        # if duration of the video is less than 30 minutes
        if duration < 1800:
            raise ValidationError(
                'Video is too short. Minimum length 30 minutes.')

        # convert upload date into Python datetime object
        upload_date = res['snippet']['publishedAt']
        upload_date = datetime.strptime(upload_date, '%Y-%m-%dT%H:%M:%SZ')

        return {'provider': 'YouTube',
                'video_id': res['id'],
                'channel_id': res['snippet']['channelId'],
                'title': res['snippet']['title'].split(' | ')[0],
                'thumbnails': res['snippet']['thumbnails'],
                'description': res['snippet']['description'],
                'tags': res['snippet']['tags'],
                'duration': duration,
                'upload_date': upload_date}

    except ValidationError:
        raise
    except Exception:
        # you would want to log this error
        raise ValidationError('Unable to fetch the video.')


def get_channel_info(video_id, youtube):
    try:
        req = youtube.videos().list(id=video_id, part='snippet')
        res = req.execute()['items'][0]
        channel_id = res['snippet']['channelId']

        # if the channel is already in our db
        if Channel.query.filter_by(channel_id=channel_id).first():
            raise ValidationError('Channel already in the database')

        # get channel's details
        part = ['snippet', 'contentDetails']
        req = youtube.channels().list(id=channel_id, part=part)
        res = req.execute()['items'][0]

        return {'channel_id': channel_id,
                'uploads_id': res['contentDetails']['relatedPlaylists']['uploads'],
                'title': res['snippet']['title'],
                'thumbnails': res['snippet']['thumbnails'],
                'description': res['snippet']['description']}
    except ValidationError:
        raise
    except Exception:
        # you would want to log this error
        raise ValidationError('Unable to fetch the channel info.')


def get_channel_videos(uploads_id):
    # videos epmty list and youtube API key
    videos, api_key = current_app.config['YOUTUBE_API_KEY'], []

    # construct youtube API service
    with build('youtube', 'v3', developerKey=api_key) as youtube:

        # first page token is None
        next_page_token = None

        # iterate through all the items in the Uploads playlist
        while True:
            try:
                scope = {'playlistId': uploads_id, 'part': 'contentDetails',
                         'maxResults': 50, 'pageToken': next_page_token}
                # every time it loops it gets the next 50 videos
                uploads = youtube.playlistItems().list(**scope).execute()
            except Exception:
                # unable to fetch the next 50 videos,
                # exit with what we got so far
                return videos

            # loop through this batch of videos
            for video in uploads['items']:
                try:
                    video_id = video['contentDetails']['videoId']
                    # this will raise exception
                    # if unable to fetch or already posted
                    video_info = get_video_info(video_id, youtube)
                    videos.append(video_info)
                except Exception:
                    continue

            # update the next page token
            next_page_token = uploads.get('nextPageToken')

            # if no more pages break the while loop
            if next_page_token is None:
                break
    return videos


def get_video_id(url):
    # Examples:
    # - https://youtu.be/SA2iWivDJiE
    # - https://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    # - https://www.youtube.com/embed/SA2iWivDJiE
    # - https://vimeo.com/534502421
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    elif query.hostname in {'www.youtube.com', 'youtube.com'}:
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path[:7] == '/embed/':
            return query.path.split('/')[2]


def convert_video_duration(duration):
    hours = re.compile(r'(\d+)H').search(duration)
    minutes = re.compile(r'(\d+)M').search(duration)
    seconds = re.compile(r'(\d+)S').search(duration)

    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0

    return (h * 3600) + (m * 60) + s
