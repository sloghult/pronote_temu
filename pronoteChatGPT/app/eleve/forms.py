from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired

class JustificationForm(FlaskForm):
    justification = TextAreaField('Justification', validators=[DataRequired()])
    submit = SubmitField('Soumettre la justification')
