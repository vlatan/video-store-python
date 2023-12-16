from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL, ValidationError

from flask_wtf import FlaskForm

from app.models import Playlist
from app.helpers import youtube_build
from app.sources.helpers import parse_playlist, validate_playlist


class PlaylistForm(FlaskForm):
    content = StringField(
        "Post YouTube Playlist URL",
        validators=[DataRequired(), URL(message="")],
        render_kw={"placeholder": "Playlist URL here..."},
    )
    submit = SubmitField("Submit")

    def __init__(self):
        super().__init__()
        self.processed_content = None

    def validate_content(self, content):
        # parse url, it will raise ValidationError if unable
        playlist_id = parse_playlist(content.data)

        # check if the playlits is already posted
        if Playlist.query.filter_by(playlist_id=playlist_id).first():
            raise ValidationError("Playlist already in the database.")

        # construct youtube API service
        with youtube_build() as youtube:
            # get the playlist's metadata
            # this will raise ValidationError if unable to fetch data
            self.processed_content = validate_playlist(playlist_id, youtube)
