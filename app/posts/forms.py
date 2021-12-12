from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError
from app.posts.helpers import parse_video, validate_video
from app.posts.helpers import parse_playlist, validate_playlist
from googleapiclient.discovery import build


class PostForm(FlaskForm):
    content = StringField('Post YouTube video URL',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Post')

    def validate_content(self, content):
        # parse url, it will raise ValidationError if unable
        video_id = parse_video(content.data)
        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            # the scope for YouTube API
            part = ['status', 'snippet', 'contentDetails']
            # construct the request for YouTube
            req = youtube.videos().list(id=video_id, part=part)
            # call YouTube API, get response (execute request)
            res = req.execute()['items'][0]
            try:
                # this will raise exception
                # if unable to fetch or already posted
                video_info = validate_video(res)
            except ValidationError:
                raise
            except Exception:
                # you would want to log this error
                raise ValidationError('Unable to fetch the video.')
        # transform the form input
        content.data = video_info


class PlaylistForm(FlaskForm):
    content = StringField('Post YouTube Playlist URL',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Post')

    def validate_content(self, content):
        # parse url, it will raise ValidationError if unable
        playlist_id = parse_playlist(content.data)
        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            # get the channel metadata
            # this will raise ValidationError if unable to fetch data
            # or if the channel is already in the database
            playlist_info = validate_playlist(playlist_id, youtube)
        # transform the form data
        content.data = playlist_info
