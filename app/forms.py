from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Email
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Stay signed in')
    submit = SubmitField('Login')


class AdminForm(FlaskForm):
    data = TextAreaField('Data', validators=[DataRequired()])
    submit_new = SubmitField('Submit to Staging')
    promote = SubmitField("Promote to Production")
    copy_prod_to_new = SubmitField("Copy Production to New")
