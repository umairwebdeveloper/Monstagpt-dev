from lib.util_wtforms import ModelForm
from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms import HiddenField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from lib.util_wtforms import choices_from_list

# class UserForm(ModelForm):

#     role = SelectField(
#         "Privileges",
#         [DataRequired()],
#         choices=choices_from_list(User.ROLE, prepend_blank=False),
#     )

#     # will need to replace User.Role with the api_keys passed in from views

class DeleteKeyForm(FlaskForm):
    api_key = HiddenField(validators=[DataRequired()])
    submit = SubmitField('Delete Key')
