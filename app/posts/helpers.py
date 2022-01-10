import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from wtforms.validators import ValidationError
from flask import abort, current_app
from app import db
from app.models import Post
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build


def validate_video(response, playlist_id=None):
    if response['status']['privacyStatus'] != 'public':
        raise ValidationError('This video is not public.')

    rating = response['contentDetails'].get('contentRating')
    if rating and rating.get('ytRating') == 'ytAgeRestricted':
        raise ValidationError('This video is age-restricted.')

    if not response['status']['embeddable']:
        raise ValidationError('This video is not embeddable.')

    if response['contentDetails'].get('regionRestriction'):
        raise ValidationError('This video is region-restricted')

    text_language = response['snippet'].get('defaultLanguage')
    if text_language and not text_language.startswith('en'):
        raise ValidationError('This video\'s title/desc is not in English')

    audio_language = response['snippet'].get('defaultAudioLanguage')
    if audio_language and not audio_language.startswith('en'):
        raise ValidationError('This video\'s audio is not in English')

    duration = convertDuration(response['contentDetails']['duration'])
    if duration.seconds < 1800:
        raise ValidationError(
            'This video is too short. Minimum length 30 minutes.')

    # convert upload date into Python datetime object
    upload_date = response['snippet']['publishedAt']
    upload_date = datetime.strptime(upload_date, '%Y-%m-%dT%H:%M:%SZ')

    # remove urls from the description
    if (description := response['snippet'].get('description')):
        description = re.sub(r'http\S+', '', description)

    # normalize title
    title = response['snippet']['title'].split(' | ')[0].split()
    ex = ['in', 'to', 'for', 'and', 'a', 'is', 'of', 'at']
    first_word = [title[0].title()]
    if (rest := title[1:]):
        rest = [w.lower() if w.lower() in ex else w.title() for w in rest]
    title = ' '.join(first_word + rest)

    return {'video_id': response['id'],
            'playlist_id': playlist_id,
            'title': title,
            'thumbnails': response['snippet']['thumbnails'],
            'description': description,
            'tags': response['snippet'].get('tags'),
            'duration': response['contentDetails']['duration'],
            'upload_date': upload_date}


def revalidate_video(post):
    # revalidate the video
    API_KEY = current_app.config['YOUTUBE_API_KEY']
    with build('youtube', 'v3', developerKey=API_KEY) as youtube:
        try:
            scope = {'id': post.video_id,
                     'part': ['status', 'snippet', 'contentDetails']}
            req = youtube.videos().list(**scope)
            # this will raise IndexError if ['items'] is empty list
            # which means the video does not exist
            res = req.execute()['items'][0]
            # this will raise ValidationError if video's invalid
            if validate_video(res):
                # number of related posts to fetch
                per_page = current_app.config['NUM_RELATED_POSTS']
                # get related posts by searching the index using the title of this post
                related_posts = Post.search(
                    post.title, 1, per_page + 1)[0].all()[1:]
                # if there's change in the related posts
                if post.related_posts != related_posts:
                    post.related_posts = related_posts
                    db.session.commit()
                # add video to index if not already there
                es = current_app.elasticsearch
                index_name, fields = Post.__tablename__, Post.__searchable__
                if es and es.ping() and not es.exists(index=index_name, id=post.id):
                    payload = {field: getattr(post, field) for field in fields}
                    es.index(index=index_name, id=post.id, document=payload)
        # video is not validated or doesn't exist
        except (IndexError, ValidationError):
            db.session.delete(post)
            db.session.commit()
            abort(404)
        except HttpError:
            # we couldn't connect to YT API,
            # so we can't evaluate the video
            pass


def validate_playlist(playlist_id, youtube):
    try:
        scope = {'id': playlist_id, 'part': 'snippet'}
        res = youtube.playlists().list(**scope).execute()['items'][0]

        channel_id = res['snippet']['channelId']
        scope = {'id': channel_id, 'part': 'snippet'}
        ch = youtube.channels().list(**scope).execute()['items'][0]

        return {'playlist_id': playlist_id,
                'channel_id': channel_id,
                'title': res['snippet']['title'],
                'thumbnails': res['snippet']['thumbnails'],
                'channel_thumbnails': ch['snippet']['thumbnails'],
                'description': res['snippet'].get('description')}

    # could not connect to YT API (HttpError)
    # or the playlist doesn't exist (IndexError)
    except (HttpError, IndexError):
        raise ValidationError('Unable to fetch the playlist.')


def parse_video(url):
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    elif 'youtube.com' in parsed.hostname:
        if parsed.path == '/watch':
            if (query := parse_qs(parsed.query).get('v')):
                return query[0]
        elif parsed.path[:7] == '/embed/':
            return parsed.path.split('/')[2]
    raise ValidationError('Unable to parse the URL')


def parse_playlist(url):
    parsed = urlparse(url)
    if parsed.hostname in ('www.youtube.com', 'youtube.com', 'youtu.be'):
        if (query := parse_qs(parsed.query).get('list')):
            return query[0]
    raise ValidationError('Unable to parse the URL')


class convertDuration(object):
    def __init__(self, iso_duration):
        self.iso = iso_duration

    def _compile(self):
        hours = re.compile(r'(\d+)H').search(self.iso)
        minutes = re.compile(r'(\d+)M').search(self.iso)
        seconds = re.compile(r'(\d+)S').search(self.iso)

        h = int(hours.group(1)) if hours else 0
        m = int(minutes.group(1)) if minutes else 0
        s = int(seconds.group(1)) if seconds else 0

        return {'h': h, 'm': m, 's': s}

    @property
    def seconds(self):
        d = self._compile()
        return (d['h'] * 3600) + (d['m'] * 60) + d['s']

    @property
    def human(self):
        d = self._compile()
        h = f"{d['h']:02d}:" if d['h'] else ''
        m, s = f"{d['m']:02d}", f":{d['s']:02d}"
        return h + m + s
