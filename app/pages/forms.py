from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired


class PageForm(FlaskForm):
    title = StringField(
        label="Title",
        validators=[DataRequired()],
        render_kw={"placeholder": "Your title..."},
    )
    content = TextAreaField(
        label="Content",
        validators=[DataRequired()],
        render_kw={"placeholder": "You can use markdown...", "rows": 15},
    )
    submit = SubmitField(label="Submit")
