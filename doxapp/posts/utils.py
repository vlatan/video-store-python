import re
import requests
from urllib.parse import urlparse, parse_qs, quote_plus
from googleapiclient.discovery import build
from flask import current_app
from wtforms.validators import ValidationError


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
                    'upload_date': resp['snippet']['publishedAt'],
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
