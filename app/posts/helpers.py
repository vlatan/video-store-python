import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from wtforms.validators import ValidationError
from app.models import Post, Channel


def validate_video(response, session=None):
    video_id = response['id']

    if session:
        # we're working with a scopped session (in a thread)
        query = session.query(Post).filter_by(video_id=video_id).first()
    else:
        # we're working within the app context
        query = Post.query.filter_by(video_id=video_id).first()

    if query:
        raise ValidationError('Video already posted')

    if response['status']['privacyStatus'] != 'public':
        raise ValidationError('Video is not public.')

    if not response['status']['embeddable']:
        raise ValidationError('Video is not embeddable.')

    if response['contentDetails'].get('regionRestriction'):
        raise ValidationError('Video is region restricted')

    text_language = response['snippet'].get('defaultLanguage')
    if text_language and text_language != 'en':
        raise ValidationError('Video\'s title/desc is not in English')

    audio_language = response['snippet'].get('defaultAudioLanguage')
    if audio_language and audio_language != 'en':
        raise ValidationError('Audio is not in English')

    duration = convert_video_duration(
        response['contentDetails']['duration'])
    if duration < 1800:
        raise ValidationError(
            'Video is too short. Minimum length 30 minutes.')

    # convert upload date into Python datetime object
    upload_date = response['snippet']['publishedAt']
    upload_date = datetime.strptime(upload_date, '%Y-%m-%dT%H:%M:%SZ')

    metadata = {'provider': 'YouTube',
                'video_id': video_id,
                'channel_id': response['snippet']['channelId'],
                'title': response['snippet']['title'].split(' | ')[0],
                'thumbnails': response['snippet']['thumbnails'],
                'description': response['snippet']['description'],
                'tags': response['snippet']['tags'],
                'duration': duration,
                'upload_date': upload_date}

    channel_id = metadata['channel_id']

    # check if this video belongs to a channel that is already in our db
    if session:
        channel = session.query(Channel).filter_by(
            channel_id=channel_id).first()
    else:
        channel = Channel.query.filter_by(channel_id=channel_id).first()

    if channel:
        # if so add the relationship to metadata
        metadata['channel'] = channel

    return metadata


def get_channel_info(video_id, youtube, session=None):
    try:
        req = youtube.videos().list(id=video_id, part='snippet')
        res = req.execute()['items'][0]
        channel_id = res['snippet']['channelId']

        if session:
            query = session.query(Channel).filter_by(
                channel_id=channel_id).first()
        else:
            query = Channel.query.filter_by(channel_id=channel_id).first()

        if query:
            # the channel is already in our db
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


def get_playlist_videos(playlist_id, youtube_service, session=None):
    # videos epmty list and first page token is None
    videos, next_page_token = [], None

    # iterate through all the items in the Uploads playlist
    while True:
        try:
            scope = {'playlistId': playlist_id, 'part': 'contentDetails',
                     'maxResults': 50, 'pageToken': next_page_token}
            # every time it loops it gets the next 50 videos
            uploads = youtube_service.playlistItems().list(**scope).execute()
        except Exception as err:
            # unable to fetch the next 50 videos,
            # exit with what we got so far
            print(err.args)
            break

        # video ids
        ids = [item['contentDetails']['videoId'] for item in uploads['items']]
        # the scope
        part = ['status', 'snippet', 'contentDetails']
        # request for YouTube for detailed info about this batch of videos
        req = youtube_service.videos().list(id=ids, part=part)
        # response from YouTube
        res = req.execute()

        # loop through this batch of videos
        for item in res['items']:
            try:
                # this will raise exception
                # if unable to fetch or already posted
                video_info = validate_video(item, session=session)
                videos.append(video_info)
            except Exception:
                # continue with this for loop
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
