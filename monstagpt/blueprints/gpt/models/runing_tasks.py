from sqlalchemy import or_
from sqlalchemy import text

from lib.util_datetime import tzware_datetime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db

class RunningTasks(ResourceMixin, db.Model):
    __tablename__ = "running_tasks"
    id = db.Column(db.Integer, primary_key=True)

    task_id = db.Column(db.String(500))
    cancelled = db.Column(db.Boolean(), nullable=True, server_default="0")

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(RunningTasks, self).__init__(**kwargs)

    def save_and_update_settings(self):
        """
        Commit the settings.

        :return: SQLAlchemy save result
        """
        self.save()
        return self.save()