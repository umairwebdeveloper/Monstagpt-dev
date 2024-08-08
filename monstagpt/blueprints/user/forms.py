from flask_wtf import FlaskForm
from wtforms import HiddenField
from wtforms import PasswordField
from wtforms import SelectField
from wtforms import StringField
from wtforms.validators import DataRequired
from wtforms.validators import Length
from wtforms.validators import Optional
from wtforms.validators import Regexp
from wtforms.validators import EqualTo
from wtforms_alchemy.validators import Unique
from wtforms_components import Email
from wtforms_components import EmailField

from config.settings import LANGUAGES
from lib.util_wtforms import ModelForm
from lib.util_wtforms import choices_from_dict
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.user.validations import (
    ensure_existing_password_matches,
)
from monstagpt.blueprints.user.validations import ensure_identity_exists


class LoginForm(FlaskForm):
    next = HiddenField()
    identity = StringField(
        "Username or email", [DataRequired(), Length(3, 254)]
    )
    password = PasswordField("Password", [DataRequired(), Length(8, 128)])
    # remember = BooleanField('Stay signed in')


class BeginPasswordResetForm(FlaskForm):
    identity = StringField(
        "Username or email",
        [DataRequired(), Length(3, 254), ensure_identity_exists],
    )


class PasswordResetForm(FlaskForm):
    reset_token = HiddenField()
    password = PasswordField("Password", [DataRequired(), Length(8, 128)])


class SignupForm(ModelForm):
    email = EmailField(
        validators=[DataRequired(), Email(), Unique(User.email)]
    )
    password = PasswordField("Password", [DataRequired(), Length(8, 128), EqualTo('confirmpassword', message='passwords do not match' )])
    confirmpassword = PasswordField("Confirm Password", [DataRequired(), Length(8, 128)])


class WelcomeForm(ModelForm):
    username_message = "Letters, numbers and underscores only please."

    username = StringField(
        validators=[
            Unique(User.username),
            DataRequired(),
            Length(1, 16),
            Regexp(r"^\w+$", message=username_message),
        ]
    )

class ConfirmEmailForm(ModelForm):
    confirmation_token = HiddenField()

class UpdateCredentialsForm(ModelForm):
    current_password = PasswordField(
        "Current password",
        [DataRequired(), Length(8, 128), ensure_existing_password_matches],
    )

    email = EmailField(validators=[Email(), Unique(User.email)])
    password = PasswordField("Password", [Optional(), Length(8, 128), EqualTo('confirmpassword', message='passwords do not match' )])
    confirmpassword = PasswordField("Confirm Password", [DataRequired(), Length(8, 128)])



class UpdateLocaleForm(FlaskForm):
    locale = SelectField(
        "Language preference",
        [DataRequired()],
        choices=choices_from_dict(LANGUAGES, prepend_blank=False),
    )
