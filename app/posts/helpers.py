import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from wtforms.validators import ValidationError
from googleapiclient.errors import HttpError
from app.models import Playlist


def validate_video(response, playlist_id=None, session=None):
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
    if text_language and text_language not in ['en', 'en-US', 'en-GB']:
        raise ValidationError('This video\'s title/desc is not in English')

    audio_language = response['snippet'].get('defaultAudioLanguage')
    if audio_language and audio_language not in ['en', 'en-US', 'en-GB']:
        raise ValidationError('This video\'s audio is not in English')

    duration = convertDuration(response['contentDetails']['duration'])
    if duration.seconds < 1800:
        raise ValidationError(
            'This video is too short. Minimum length 30 minutes.')

    # convert upload date into Python datetime object
    upload_date = response['snippet']['publishedAt']
    upload_date = datetime.strptime(upload_date, '%Y-%m-%dT%H:%M:%SZ')

    metadata = {'provider': 'YouTube',
                'video_id': response['id'],
                'playlist_id': playlist_id,
                'title': response['snippet']['title'].split(' | ')[0],
                'thumbnails': response['snippet']['thumbnails'],
                'description': response['snippet'].get('description'),
                'tags': response['snippet'].get('tags'),
                'duration': response['contentDetails']['duration'],
                'upload_date': upload_date}

    return metadata


def lookup_playlist(playlist_id, session=None):
    if session:
        playlist = session.query(Playlist).filter_by(
            playlist_id=playlist_id).first()
    else:
        playlist = Playlist.query.filter_by(playlist_id=playlist_id).first()
    return playlist


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


def get_playlist_videos(playlist_id, youtube_service, session=None):
    # videos epmty list and first page token is None
    videos, next_page_token = [], None

    # iterate through all the items in the Uploads playlist
    while True:
        try:
            # scope for creating a batch of 50 from the playlist
            scope = {'playlistId': playlist_id, 'part': 'contentDetails',
                     'maxResults': 50, 'pageToken': next_page_token}
            # every time it loops it gets the next 50 videos
            uploads = youtube_service.playlistItems().list(**scope).execute()

            # scope for detalied info about each video in this batch
            scope = {'id': [item['contentDetails']['videoId']
                            for item in uploads['items']],
                     'part': ['status', 'snippet', 'contentDetails']}
            # response from YouTube
            res = youtube_service.videos().list(**scope).execute()
        except HttpError:
            # failed to connect to YT API
            # we abandon further operation
            # because we don't have the next token
            break

        # loop through this batch of videos
        # if there are no videos res['items'] will be empty list
        for item in res['items']:
            try:
                # this will raise exception if video's invalid
                video_info = validate_video(
                    item, playlist_id=playlist_id, session=session)
                # lookup playlist in our db
                playlist = lookup_playlist(playlist_id, session=session)
                # if it exists
                if playlist:
                    # add this relationship to the video metadata
                    video_info['playlist'] = playlist
                videos.append(video_info)
            except ValidationError:
                # video not validated
                # continue, try the next video
                continue

        # update the next page token
        next_page_token = uploads.get('nextPageToken')

        # if no more pages break the while loop, we're done
        if next_page_token is None:
            break

    return videos


def parse_video(url):
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    elif parsed.hostname in {'www.youtube.com', 'youtube.com'}:
        if parsed.path == '/watch':
            query = parse_qs(parsed.query).get('v')
            if query:
                return query[0]
        elif parsed.path[:7] == '/embed/':
            return parsed.path.split('/')[2]
    raise ValidationError('Unable to parse the URL')


def parse_playlist(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query).get('list')
    if query:
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
