from lib.util_datetime import tzware_datetime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.extensions import db

class Api(ResourceMixin, db.Model):
    __tablename__ = "api"
    id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", onupdate="CASCADE",ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user = db.relationship("User",viewonly=True)

    api_key = db.Column(db.String(50),unique=True)

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(Api, self).__init__(**kwargs)

    def add_key(self,user):
        """
        Add an api key for the user

        :return: SQLALchemy save result
        """
        self.save()
        return user.save()
    
    def save_and_update_user(self, user):
        """
        Add/remove api key and update the user's information.

        :return: SQLAlchemy save result
        """
        self.save()
        return user.save()
        None


    def delete_and_update_user(self, user, api_key):
        """
        Delete the api key and update the user's information.

        :return: SQLAlchemy delete result
        """
        
        api_object = Api.query.filter_by(user_id=user.id, api_key=api_key).first()

        if api_object:
            db.session.delete(api_object)
            db.session.commit()
            return user.save()
        return None
    
    def check_api_key_exists(self, user, api_key):
        """
        Check if an api key exists for a given user.

        :return: Boolean
        """
        api_object = Api.query.filter_by(user_id=user.id, api_key=api_key).first()
        return api_object is not None
    
    def find_user_by_api_key(self, api_key):
        """
        Find the user associated with a given api key.

        :return: User instance or None
        """
        api_object = Api.query.filter_by(api_key=api_key).first()
        if api_object:
            return api_object.user  # Return the User instance associated with this Api instance
        else:
            return None