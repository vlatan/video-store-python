from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError
from doxapp.posts.utils import (extract_video_id,
                                fetch_youtube_data, fetch_vimeo_data)


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
        # if it's a YouTube video
        if video_id[0] == 'youtube':
            video_data = fetch_youtube_data(video_id[1])
        # if it's a Vimeo video
        else:
            video_data = fetch_vimeo_data(video_id[1])
        # transform the form input
        content.data = video_data
