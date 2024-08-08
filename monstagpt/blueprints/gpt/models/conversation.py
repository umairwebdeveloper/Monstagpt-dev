from sqlalchemy import or_
from sqlalchemy import text

from lib.util_datetime import tzware_datetime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db

class Conversation(ResourceMixin, db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", onupdate="CASCADE",ondelete="CASCADE"),
        index=True,
        nullable=False
    )


    user_deleted = db.Column(db.Boolean(), nullable=True, server_default="0")

    conversation_name = db.Column(db.String(500), unique=False, nullable=False)
    conversation_uuid = db.Column(db.String(500), unique=True, nullable=False)
    assistant_type = db.Column(db.String(10), nullable=True, server_default="")

    # Relationship to the Gpt model
    questions = db.relationship('Gpt', backref='conversation', lazy=True)

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Conversation, self).__init__(**kwargs)

    def save(self):
        """
        Save the conversation.

        :return: SQLAlchemy save result
        """
        db.session.add(self)
        db.session.commit()
        return self
