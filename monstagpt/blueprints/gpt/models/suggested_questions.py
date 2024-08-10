from sqlalchemy import or_
from sqlalchemy import text

from lib.util_datetime import tzware_datetime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db

class Suggested(ResourceMixin,db.Model):
    __tablename__ = "suggested"
    id = db.Column(db.Integer, primary_key=True)

    question = db.Column(db.String(5000),nullable=False)
    order = db.Column(db.Integer(),nullable=False)


    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Suggested, self).__init__(**kwargs)


    def save(self):
        """
        Save a model instance.

        :return: Model instance
        """
        return self.save()