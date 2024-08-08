from collections import OrderedDict
from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms import HiddenField
from wtforms.validators import DataRequired
from wtforms.validators import Length
from lib.util_wtforms import choices_from_dict
from wtforms_components import EmailField

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

class ConversationForm(FlaskForm):
    conversation = TextAreaField(
        "Enter a new name for the conversation", [DataRequired(), Length(max=4000)]
    )

class QuestionForm(FlaskForm):
    questionInput = TextAreaField(
        "Ask your question here", [DataRequired(), Length(max=4000)]
    )


class FeedbackForm(FlaskForm):
    question = TextAreaField(
        "Question", [DataRequired(), Length(max=4000),],render_kw={"id": "modalQuestion"}
    )
    answer = TextAreaField(
        "Response", [DataRequired(), Length(max=4000)],render_kw={"id": "modalAnswer"}
    )
    thread_id = HiddenField(render_kw={"id": "modalThread"})

    message = TextAreaField(
        "Additional information", [DataRequired(), Length(1, 8192)],render_kw={"id": "modalMessage"}
    )
