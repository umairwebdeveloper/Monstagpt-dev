from lib.util_datetime import tzware_datetime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db

class Oaistatus(ResourceMixin, db.Model):
    __tablename__ = "oaistatus"
    id = db.Column(db.Integer, primary_key=True)

    incident_name = db.Column(db.String(100),unique=True)
    incident_status = db.Column(db.String(500),unique=True)
    incident_id = db.Column(db.String(50),unique=True)


    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Oaistatus, self).__init__(**kwargs)

    @classmethod
    def update_records(cls, incident_id, incident_name, incident_status):
        record = cls.query.filter_by(incident_id=incident_id).first()
        if record:
            record.incident_name = incident_name
            record.incident_status = incident_status
            message = "Record updated."
        else:
            record = cls(incident_id=incident_id, incident_name=incident_name, incident_status=incident_status)
            db.session.add(record)
            message = "New record created."
        
        db.session.commit()
        return message

    @classmethod
    def delete_record(cls, incident_id):
        record = cls.query.filter_by(incident_id=incident_id).first()
        if record:
            db.session.delete(record)
            db.session.commit()
        return None
    


