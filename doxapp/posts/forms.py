from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError
from doxapp.posts.utils import extract_video_id, get_video_info
from googleapiclient.discovery import build


class PostForm(FlaskForm):
    title = StringField('Title')
    content = StringField('Video URL (YouTube or Vimeo)',
                          validators=[DataRequired(), URL()])
    submit = SubmitField('Post')

    def validate_content(self, content):
        # parse url
        video_id = extract_video_id(content.data)
        # if unable to parse video ID
        if video_id is None:
            raise ValidationError('Unable to parse the URL')
        # construct youtube API service
        api_key = current_app.config['YOUTUBE_API_KEY']
        with build('youtube', 'v3', developerKey=api_key) as youtube:
            # get the video metadata
            # this will raise ValidationError if unable to fetch data
            video_info = get_video_info(video_id, youtube)
        # transform the form input
        content.data = video_info
