import re
import json
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs, quote_plus
from googleapiclient.discovery import build
from flask import current_app
from wtforms.validators import ValidationError
from threading import Timer, Lock


class Periodic(object):
    """ A periodic task running in threading.Timers """
    # https://stackoverflow.com/a/18906292

    def __init__(self, interval, function, *args, **kwargs):
        self._lock = Lock()
        self._timer = None
        self.function = function
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self._stopped = True
        if kwargs.pop('autostart', True):
            self.start()

    def start(self, from_run=False):
        self._lock.acquire()
        if from_run or self._stopped:
            self._stopped = False
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self._lock.release()

    def _run(self):
        self.start(from_run=True)
        self.function(*self.args, **self.kwargs)

    def stop(self):
        self._lock.acquire()
        self._stopped = True
        self._timer.cancel()
        self._lock.release()


def get_playlist_id(chanel_id, playlist_name, youtube):
    try:
        # get channel's details
        res = youtube.channels().list(id=chanel_id, part='contentDetails').execute()
        # retrieve the Uploads' playlist id
        return res['items'][0]['contentDetails']['relatedPlaylists'][playlist_name]
    except Exception:
        return None


def get_video_metadata(video_id, youtube):
    # the scope we want per video
    part = ['status', 'snippet', 'contentDetails']
    # construct the request
    req = youtube.videos().list(id=video_id, part=part)
    # get response (execute request)
    res = req.execute()['items'][0]

    embeddable = res['status']['embeddable']
    restricted = res['contentDetails'].get('regionRestriction')
    # duration of the video
    duration = res['contentDetails']['duration']
    duration = convert_video_duration(duration)

    # if the video is embeddable and not region restricted
    # and longer than 30 minutes
    # CHECK FOR PRIVACY HERE TOO
    if embeddable and not restricted and duration > 1800:
        return {'video_id': res['id'],
                'chanel_id': res['snippet']['channelId'],
                'upload_date': res['snippet']['publishedAt'],
                'title': res['snippet']['title'].split(' | ')[0],
                'thumbnails': res['snippet']['thumbnails'],
                'description': res['snippet']['description'],
                'duration': duration}


def get_channel_videos(chanel_id, already_posted):
    # videos epmty list and youtube API key
    videos, api_key = current_app.config['YOUTUBE_API_KEY'], []

    # construct youtube API service
    with build('youtube', 'v3', developerKey=api_key) as youtube:
        # get uploads playlist id
        uploads_id = get_playlist_id(chanel_id, 'uploads', youtube)
        # first page token is None
        next_page_token = None

        # iterate through all the items in the Uploads playlist
        while True:
            try:
                # get 50 items
                uploads = youtube.playlistItems().list(playlistId=uploads_id,
                                                       part='contentDetails',
                                                       maxResults=50,
                                                       pageToken=next_page_token).execute()
            except Exception:
                return videos

            # loop through this batch of videos
            for video in uploads['items']:
                try:
                    # get the video id
                    video_id = video['contentDetails']['videoId']
                    # if video is NOT in our DB
                    if video_id not in already_posted:
                        metadata = get_video_metadata(video_id, youtube)
                        if metadata:
                            videos.append(metadata)
                except Exception:
                    continue

            # update the next page token
            next_page_token = uploads.get('nextPageToken')

            # if no more pages break the while loop
            if next_page_token is None:
                break
    return videos


def extract_video_id(url):
    # Examples:
    # - https://youtu.be/SA2iWivDJiE
    # - https://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    # - https://www.youtube.com/embed/SA2iWivDJiE
    # - https://vimeo.com/534502421
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return ('youtube', query.path[1:])
    elif query.hostname in {'www.youtube.com', 'youtube.com'}:
        if query.path == '/watch':
            return ('youtube', parse_qs(query.query)['v'][0])
        if query.path[:7] == '/embed/':
            return ('youtube', query.path.split('/')[2])
    elif query.hostname in {'www.vimeo.com', 'vimeo.com'}:
        return ('vimeo', query.path.lstrip('/'))


def fetch_youtube_data(video_id):
    api_key = current_app.config['YOUTUBE_API_KEY']
    # construct service
    with build('youtube', 'v3', developerKey=api_key) as youtube:
        try:
            # the scope
            part = ['status', 'snippet', 'contentDetails']
            # construct the request for YouTube
            req = youtube.videos().list(id=video_id, part=part)
            # get response (execute request)
            resp = req.execute()['items'][0]
            # if video not embeddable (this is a boolean value)
            if not resp['status']['embeddable']:
                raise ValidationError('Video is not embeddable.')
            # if video geo-restricted (None if no region restrictions)
            if resp['contentDetails'].get('regionRestriction'):
                raise ValidationError('Video is region restricted')
            # duration of the video
            duration = resp['contentDetails']['duration']
            duration = convert_video_duration(duration)
            # if duration of the video is less than 30 minutes
            if duration < 1800:
                raise ValidationError(
                    'Video is too short. Minimum length 30 minutes.')

            return {'id': resp['id'],
                    'upload_date': datetime.strptime(resp['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                    'provider_title': resp['snippet']['title'],
                    'thumbnails': resp['snippet']['thumbnails'],
                    'duration': duration,
                    'provider_name': 'YouTube'}

        except ValidationError:
            raise
        except Exception:
            # you would want to log this error
            raise ValidationError('Unable to fetch the video.')


def convert_video_duration(duration):
    hours = re.compile(r'(\d+)H').search(duration)
    minutes = re.compile(r'(\d+)M').search(duration)
    seconds = re.compile(r'(\d+)S').search(duration)

    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0

    return (h * 3600) + (m * 60) + s


def fetch_vimeo_data(video_id):
    url = quote_plus(f'https://vimeo.com/{video_id}')
    oembed = f'https://vimeo.com/api/oembed.json?url={url}&width=1280'
    try:
        response = requests.get(oembed)
        if response.ok:
            video_data = response.json()
            if video_data['duration'] < 1800:
                raise ValidationError(
                    'Video is too short. Minimum length 30 minutes.')
            return {'id': video_data['video_id'],
                    'upload_date': video_data['upload_date'],
                    'provider_title': video_data['title'],
                    'thumbnail': video_data['thumbnail_url'],
                    'duration': video_data['duration'],
                    'provider_name': 'Vimeo'}
        else:
            raise ValidationError('Unable to fetch the video.')
    except ValidationError:
        raise
    except Exception:
        raise ValidationError('Unable to fetch the video.')
