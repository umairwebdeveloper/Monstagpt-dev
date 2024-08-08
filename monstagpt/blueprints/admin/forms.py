from collections import OrderedDict
from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import DateTimeField
from wtforms import FloatField
from wtforms import IntegerField
from wtforms import SelectField
from wtforms import StringField
from wtforms import TextAreaField
from wtforms import SubmitField
from wtforms.validators import InputRequired, NumberRange
from wtforms.validators import DataRequired
from wtforms.validators import Length
from wtforms.validators import NumberRange
from wtforms.validators import Optional
from wtforms.validators import Regexp
from wtforms_alchemy.validators import Unique
from wtforms_components import DateRange
from lib.locale import Currency
from lib.util_wtforms import ModelForm
from lib.util_wtforms import choices_from_dict
from monstagpt.blueprints.billing.models.coupon import Coupon
from monstagpt.blueprints.user.models import User

class SearchForm(FlaskForm):
    q = StringField("Search terms", [Optional(), Length(1, 256)])


class BulkDeleteForm(FlaskForm):
    SCOPE = OrderedDict(
        [
            ("all_selected_items", "All selected items"),
            ("all_search_results", "All search results"),
        ]
    )

    scope = SelectField(
        "Privileges",
        [DataRequired()],
        choices=choices_from_dict(SCOPE, prepend_blank=False),
    )


class UserForm(ModelForm):
    username_message = "Letters, numbers and underscores only please."

    subscribed_coins = IntegerField(
        "Subscribed tokens", [InputRequired(), NumberRange(min=0, max=2147483647)]
    )

    bought_coins = IntegerField(
        "Bought tokens", [InputRequired(), NumberRange(min=0, max=2147483647)]
    )

    free_coins = IntegerField(
            "Free tokens", [InputRequired(), NumberRange(min=0, max=2147483647)]
        )

    requested_tokens = BooleanField("User can request free tokens")

    insights_keys = TextAreaField(
        "Insights API keys", [Length(0, 500)]
    )

    data_marketplace_bucket = TextAreaField(
        "Data marketplace S3 bucket", [Length(0, 500)]
    )

    username = StringField(
        validators=[
            Unique(User.username),
            Optional(),
            Length(1, 16),
            Regexp(r"^\w+$", message=username_message),
        ]
    )

    role = SelectField(
        "Privileges",
        [DataRequired()],
        choices=choices_from_dict(User.ROLE, prepend_blank=False),
    )
    active = BooleanField("Yes, allow this user to sign in")


class UserCancelSubscriptionForm(FlaskForm):
    pass


class CouponForm(ModelForm):
    redeem_by_msg = "Datetime must be in the future."

    percent_off = IntegerField(
        "Percent off (%)", [Optional(), NumberRange(min=1, max=100)]
    )
    amount_off = FloatField(
        "Amount off ($)", [Optional(), NumberRange(min=0.01, max=21474836.47)]
    )

    code = StringField("Code", [DataRequired(), Length(1, 32)])
    currency = SelectField(
        "Currency",
        [DataRequired()],
        choices=choices_from_dict(Currency.TYPES, prepend_blank=False),
    )
    duration = SelectField(
        "Duration",
        [DataRequired()],
        choices=choices_from_dict(Coupon.DURATION, prepend_blank=False),
    )
    duration_in_months = IntegerField(
        "Duration in months", [Optional(), NumberRange(min=1, max=12)]
    )
    max_redemptions = IntegerField(
        "Max Redemptions", [Optional(), NumberRange(min=1, max=2147483647)]
    )
    redeem_by = DateTimeField(
        "Redeem by",
        [Optional(), DateRange(min=datetime.now(), message=redeem_by_msg)],
        format="%Y-%m-%d %H:%M:%S",
    )

    def validate(self):
        if not FlaskForm.validate(self):
            return False

        result = True

        code = self.code.data.upper()
        percent_off = self.percent_off.data
        amount_off = self.amount_off.data

        if Coupon.query.filter(Coupon.code == code).first():
            unique_error = "Already exists."
            self.code.errors.append(unique_error)
            result = False
        elif percent_off is None and amount_off is None:
            empty_error = "Pick at least one."
            self.percent_off.errors.append(empty_error)
            self.amount_off.errors.append(empty_error)
            result = False
        elif percent_off and amount_off:
            both_error = "Cannot pick both."
            self.percent_off.errors.append(both_error)
            self.amount_off.errors.append(both_error)
            result = False
        else:
            pass

        return result

class ItemForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])


class GPTInstructionsForm(FlaskForm):
    instructions = TextAreaField(
        "GPT instructions", [DataRequired(), Length(1, 50000)]
    )

class AllowSignupsForm(ModelForm):
    allow_signup = BooleanField("Allow new signups")

class RateForm(FlaskForm):
    tier = StringField('Tier', validators=[DataRequired()])
    rate_limit_seconds = IntegerField('Rate Limit (Seconds)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit')