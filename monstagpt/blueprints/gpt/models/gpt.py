from sqlalchemy import or_
from sqlalchemy import text

from lib.util_datetime import tzware_datetime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db


class Gpt(ResourceMixin, db.Model):
    __tablename__ = "gpt"
    id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", onupdate="CASCADE",ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user = db.relationship("User",viewonly=True)

    conversation_uuid = db.Column(db.String(500), db.ForeignKey('conversations.conversation_uuid'), nullable=False)
    user_deleted = db.Column(db.Boolean(), nullable=True, server_default="0")

    # Question details
    question = db.Column(db.String(500))
    answer = db.Column(db.String(5000))
    prompt_tokens = db.Column(db.Integer())
    completion_tokens = db.Column(db.Integer())
    total_cost = db.Column(db.Float())
    sql = db.Column(db.String(5000))

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Gpt, self).__init__(**kwargs)

    def save_and_update_user(self, user, error=False):
        """
        Commit the question and update the user's information.

        :return: SQLAlchemy save result
        """
        self.save()
        if error:
            # user.last_question_on = tzware_datetime()
            # return user.save()
            return None

        # if user.role != 'vip':
        #     user.use_coins(1)
        user.last_gpt_question = tzware_datetime().timestamp()
        return user.save()
    
    def to_json(self):
        """
        Return JSON fields to represent a question/answer.

        :return: dict
        """
        params = {
            "question": self.question,
            "answer": self.answer,
        }

        return params
    
    @classmethod
    def search(cls, query):
        """
        Search a resource by 1 or more fields.

        :param query: Search query
        :type query: str
        :return: SQLAlchemy filter
        """
        from monstagpt.blueprints.user.models import User

        if query == "":
            return text("")

        search_query = "%{0}%".format(query)
        search_chain = (
            User.email.ilike(search_query),
            User.username.ilike(search_query),
            cls.question.ilike(search_query),
        )

        return or_(*search_chain)