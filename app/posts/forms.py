from googleapiclient.errors import HttpError
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError

from flask_wtf import FlaskForm

from app.models import Post
from app.helpers import youtube_build
from app.posts.helpers import parse_video, validate_video, fetch_video_data


class PostForm(FlaskForm):
    content = StringField(
        "Post YouTube Video URL",
        validators=[DataRequired(), URL(message="")],
        render_kw={"placeholder": "Video URL here..."},
    )
    submit = SubmitField("Submit")

    def __init__(self):
        super().__init__()
        self.processed_content = None

    def validate_content(self, content):
        # parse url, it will raise ValidationError if unable
        video_id = parse_video(content.data)

        # check if the video is already posted
        if Post.query.filter_by(video_id=video_id).first():
            raise ValidationError("Video already posted.")

        # construct youtube API service
        with youtube_build() as youtube:
            try:
                # the scope for YouTube API
                part = ["status", "snippet", "contentDetails"]
                # construct the request for YouTube
                req = youtube.videos().list(id=video_id, part=part)
                # call YouTube API, get response (execute request)
                res = req.execute()["items"][0]
                # this will raise exception if unable to fetch
                if validate_video(res):
                    self.processed_content = fetch_video_data(res)
            # if video's not valid
            except ValidationError:
                # re-raise the exception thrown from validate_video()
                raise
            # if ['items'] list is empty or unable to connect to YT API
            except (HttpError, IndexError):
                raise ValidationError("Unable to fetch the video.")
