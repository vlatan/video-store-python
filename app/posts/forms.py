from flask import current_app
from flask_wtf import FlaskForm
from googleapiclient.errors import HttpError
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError
from app.models import Post, Playlist
from app.posts.helpers import parse_video, validate_video, fetch_video_data
from app.posts.helpers import parse_playlist, validate_playlist
from googleapiclient.discovery import build


class PostForm(FlaskForm):
    content = StringField('Post YouTube Video URL',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Submit')

    def validate_content(self, content):
        # parse url, it will raise ValidationError if unable
        video_id = parse_video(content.data)

        # check if the video is already posted
        if Post.query.filter_by(video_id=video_id).first():
            raise ValidationError('Video already posted')

        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            try:
                # the scope for YouTube API
                part = ['status', 'snippet', 'contentDetails']
                # construct the request for YouTube
                req = youtube.videos().list(id=video_id, part=part)
                # call YouTube API, get response (execute request)
                res = req.execute()['items'][0]
                # this will raise exception if unable to fetch
                if validate_video(res):
                    video_info = fetch_video_data(res)
            # if video's not valid
            except ValidationError:
                # re-raise the exception thrown from validate_video()
                raise
            # if ['items'] list is empty or unable to connect to YT API
            except (HttpError, IndexError):
                raise ValidationError('Unable to fetch the video.')

        # transform the form input
        content.data = video_info


class PlaylistForm(FlaskForm):
    content = StringField('Post YouTube Playlist URL',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Submit')

    def validate_content(self, content):
        # parse url, it will raise ValidationError if unable
        playlist_id = parse_playlist(content.data)

        # check if the playlits is already posted
        if Playlist.query.filter_by(playlist_id=playlist_id).first():
            raise ValidationError('Playlist already in the database')

        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            # get the playlist's metadata
            # this will raise ValidationError if unable to fetch data
            playlist_info = validate_playlist(playlist_id, youtube)

        # transform the form data
        content.data = playlist_info
