from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError
from doxapp.posts.utils import get_video_id, get_video_info, get_channel_info
from googleapiclient.discovery import build


class PostForm(FlaskForm):
    content = StringField('Post YouTube video URL',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Post')

    def validate_content(self, content):
        # parse url
        video_id = get_video_id(content.data)
        # if unable to parse video ID
        if video_id is None:
            raise ValidationError('Unable to parse the URL')
        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            # get the video metadata
            # this will raise ValidationError if unable to fetch data
            # or if the video is already in the database
            video_info = get_video_info(video_id, youtube)
        # transform the form input
        content.data = video_info


class ChannelForm(FlaskForm):
    content = StringField('Post YouTube video URL to get the channel info',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Post')

    def validate_content(self, content):
        # parse url
        video_id = get_video_id(content.data)
        # if unable to parse video ID
        if video_id is None:
            raise ValidationError('Unable to parse the URL')
        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            # get the channel metadata
            # this will raise ValidationError if unable to fetch data
            # or if the channel is already in the database
            channel_info = get_channel_info(video_id, youtube)
        # transform the form input
        content.data = channel_info
