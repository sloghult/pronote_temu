from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, SubmitField, DateField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime

class NoteForm(FlaskForm):
    eleve_id = SelectField("Élève", coerce=int, validators=[DataRequired()])
    matiere_id = SelectField("Matière", coerce=int, validators=[DataRequired()])
    note = FloatField("Note", validators=[DataRequired(), NumberRange(min=0, max=20)])
    coef = FloatField("Coefficient", default=1, validators=[DataRequired(), NumberRange(min=0.1, max=10)])  # Ajout du coef
    submit = SubmitField("Ajouter la note")
    classe_id = SelectField('Classe', coerce=int)  # Ajout du champ classe

class AppelForm(FlaskForm):
    classe_id = SelectField('Classe', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=datetime.now)
    creneau = SelectField('Créneau', choices=[
        ('8h-9h', '8h-9h'),
        ('9h-10h', '9h-10h'),
        ('10h-11h', '10h-11h'),
        ('11h-12h', '11h-12h'),
        ('14h-15h', '14h-15h'),
        ('15h-16h', '15h-16h'),
        ('16h-17h', '16h-17h')
    ], validators=[DataRequired()])
    submit = SubmitField('Suivant')
