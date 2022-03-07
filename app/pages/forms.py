from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired


class PageForm(FlaskForm):
    title = StringField(label='Title', validators=[DataRequired()])
    content = TextAreaField(label='Text', validators=[DataRequired()],
                            render_kw={'placeholder': 'Enter text...You can use markdown.'})
    submit = SubmitField(label='Submit')
