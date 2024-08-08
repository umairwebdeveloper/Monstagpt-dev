import datetime
from collections import OrderedDict

import pytz
from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import or_
from sqlalchemy import text
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from lib.security import sign_token
from lib.security import verify_token
from lib.util_sqlalchemy import AwareDateTime
from lib.util_sqlalchemy import ResourceMixin
from monstagpt.blueprints.billing.models.credit_card import CreditCard
from monstagpt.blueprints.billing.models.invoice import Invoice
from monstagpt.blueprints.billing.models.subscription import Subscription
from monstagpt.blueprints.api.models import Api
from monstagpt.blueprints.gpt.models.gpt import Gpt
from monstagpt.blueprints.stripe_payments.models import ProductCatalog

from monstagpt.extensions import db


class User(UserMixin, ResourceMixin, db.Model):
    ROLE = OrderedDict([("member", "Member"), ("admin", "Admin"), ("vip", "VIP")])

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    # Relationships.
    credit_card = db.relationship(
        CreditCard, uselist=False, backref="credit_card", passive_deletes=True
    )
    subscription = db.relationship(
        Subscription,
        uselist=False,
        backref="subscription",
        passive_deletes=True,
    )
    invoices = db.relationship(
        Invoice, backref="invoices", passive_deletes=True
    )

    api = db.relationship(
        Api,
        backref = 'api',
        passive_deletes=True,
    )

    gpt = db.relationship(
        Gpt,
        backref = 'gpt',
        passive_deletes=True,
    )

    # Authentication.
    role = db.Column(
        db.Enum(*ROLE, name="role_types", native_enum=False),
        index=True,
        nullable=False,
        server_default="member",
    )
    active = db.Column(
        "is_active", db.Boolean(), nullable=False, server_default="1"
    )
    username = db.Column(db.String(24), unique=True, index=True)
    email = db.Column(
        db.String(255),
        unique=True,
        index=True,
        nullable=False,
        server_default="",
    )
    password = db.Column(db.String(128), nullable=False, server_default="")

    # Billing.
    name = db.Column(db.String(128), index=True)
    customer_id = db.Column(db.String(128), index=True)
    cancelled_subscription_on = db.Column(AwareDateTime())
    previous_plan = db.Column(db.String(128))

    # gpt.
    has_seen_pricing = db.Column(db.Boolean(), nullable=False, server_default="0")
    subscribed_coins = db.Column(db.Integer, default=0)
    bought_coins = db.Column(db.Integer, default=0)
    free_coins = db.Column(db.Integer, default=0)
    last_gpt_question = db.Column(db.Integer())
    requested_tokens = db.Column(db.Boolean, nullable=False, default=True)

    # insights api
    insights_keys = db.Column(db.String(400))

    # Data marketplace
    data_marketplace_bucket = db.Column(db.String(400))

    # Activity tracking.
    sign_in_count = db.Column(db.Integer, nullable=False, default=0)
    current_sign_in_on = db.Column(AwareDateTime())
    current_sign_in_ip = db.Column(db.String(45))
    last_sign_in_on = db.Column(AwareDateTime())
    last_sign_in_ip = db.Column(db.String(45))

    # Confirmed email
    account_is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    account_confirmed_on = db.Column(AwareDateTime(), nullable=True)

    # Additional settings.
    locale = db.Column(db.String(5), nullable=False, server_default="en")

    def __init__(self, **kwargs):
        # Call Flask-SQLAlchemy's constructor.
        super(User, self).__init__(**kwargs)

        self.password = User.encrypt_password(kwargs.get("password", ""))
        self.subscribed_coins = 0
        self.bought_coins = 0
        self.free_coins = 10
        self.last_gpt_question = 0

    @classmethod
    def find_by_identity(cls, identity):
        """
        Find a user by their e-mail or username.

        :param identity: Email or username
        :type identity: str
        :return: User instance
        """
        return User.query.filter(
            (User.email == identity) | (User.username == identity)
        ).first()

    @classmethod
    def find_by_token(cls, token, ex=3600):
        """
        Obtain a user by looking up their email contained in a token.

        :param token: Signed token.
        :type token: str
        :param expiration: Seconds until it expires, defaults to 1 hour
        :type expiration: int
        :return: User instance or None
        """
        email = verify_token(token, ex)

        if email is None:
            return None

        return User.find_by_identity(email)

    @classmethod
    def encrypt_password(cls, plaintext_password):
        """
        Hash a plaintext string using PBKDF2. This is good enough according
        to the NIST (National Institute of Standards and Technology).

        In other words while bcrypt might be superior in practice, if you use
        PBKDF2 properly (which we are), then your passwords are safe.

        :param plaintext_password: Password in plain text
        :type plaintext_password: str
        :return: str
        """
        if plaintext_password:
            return generate_password_hash(plaintext_password)

        return None

    @classmethod
    def initialize_password_reset(cls, identity):
        """
        Generate a token to reset the password for a specific user.

        :param identity: User e-mail address or username
        :type identity: str
        :return: User instance
        """
        u = User.find_by_identity(identity)
        reset_token = sign_token(u.email)

        # This prevents circular imports.
        from monstagpt.blueprints.user.tasks import (
            deliver_password_reset_email,
        )

        deliver_password_reset_email.delay(u.id, reset_token)

        return u


    @classmethod
    def initialize_confirmation_email(cls, identity):
        """
        Generate a token for the user to confirm their email
        :param identity: User e-mail address
        :type identity: str
        :return: User instance
        """

        u = User.find_by_identity(identity)
        confirmation_token = sign_token(u.email)

         # This prevents circular imports.
        from monstagpt.blueprints.user.tasks import (
            deliver_confirmation_email)
        deliver_confirmation_email.delay(u.id, confirmation_token)

        return u

    @classmethod
    def search(cls, query):
        """
        Search a resource by 1 or more fields.

        :param query: Search query
        :type query: str
        :return: SQLAlchemy filter
        """
        if query == "":
            return text("")

        search_query = "%{0}%".format(query)
        search_chain = (
            User.email.ilike(search_query),
            User.username.ilike(search_query),
        )

        return or_(*search_chain)

    @classmethod
    def is_last_admin(cls, user, new_role, new_active):
        """
        Determine whether or not this user is the last admin account.

        :param user: User being tested
        :type user: User
        :param new_role: New role being set
        :type new_role: str
        :param new_active: New active status being set
        :type new_active: bool
        :return: bool
        """
        is_demoting_admin = user.role == "admin" and new_role != "admin"
        is_changing_active = user.active is True and new_active is None
        admin_count = User.query.filter(User.role == "admin").count()

        if is_demoting_admin and admin_count == 1:
            return True

        if is_changing_active and user.role == "admin" and admin_count == 1:
            return True

        return False

    @classmethod
    def bulk_delete(cls, ids):
        """
        Override the general bulk_delete method because we need to delete them
        one at a time while also deleting them on Stripe.

        :param ids: List of ids to be deleted
        :type ids: list
        :return: int
        """
        delete_count = 0

        for id in ids:
            user = User.query.get(id)

            if user is None:
                continue

            if user.customer_id is None:
                user.delete()
            else:
                subscription = Subscription()
                cancelled = subscription.cancel(user=user)

                # If successful, delete it locally.
                if cancelled:
                    user.delete()

            delete_count += 1

        return delete_count

    def is_active(self):
        """
        Return whether or not the user account is active, this satisfies
        Flask-Login by overwriting the default value.

        :return: bool
        """
        return self.active

    def authenticated(self, with_password=True, password=""):
        """
        Ensure a user is authenticated, and optionally check their password.

        :param with_password: Optionally check their password
        :type with_password: bool
        :param password: Optionally verify this as their password
        :type password: str
        :return: bool
        """
        if with_password:
            return check_password_hash(self.password, password)

        return True

    def serialize_token(self, expiration=3600):
        """
        Sign and create a token that can be used for things such as resetting
        a password or other tasks that involve a one off token.

        :param expiration: Seconds until it expires, defaults to 1 hour
        :type expiration: int
        :return: JSON
        """
        private_key = current_app.config["SECRET_KEY"]

        serializer = URLSafeTimedSerializer(private_key, expiration)
        return serializer.dumps({"user_email": self.email}).decode("utf-8")

    def update_activity_tracking(self, ip_address):
        """
        Update various fields on the user that's related to meta data on their
        account, such as the sign in count and ip address, etc..

        :param ip_address: IP address
        :type ip_address: str
        :return: SQLAlchemy commit results
        """
        self.sign_in_count += 1

        self.last_sign_in_on = self.current_sign_in_on
        self.last_sign_in_ip = self.current_sign_in_ip

        self.current_sign_in_on = datetime.datetime.now(pytz.utc)
        self.current_sign_in_ip = ip_address

        return self.save()

    def add_coins(self, plan):
        """
        Add an amount of coins to an existing user.

        :param plan: Subscription plan
        :type plan: str
        :return: SQLAlchemy commit results
        """
        self.coins += plan["metadata"]["coins"]

        return self.save()

    @property
    def coins(self):
        """Total coins the user has."""
        return self.subscribed_coins + self.bought_coins + self.free_coins
    
    def use_coins(self, amount):
        """Use coins, consuming free_coins first, then subscribed_coins, and finally bought_coins."""
        if amount > self.coins:
            raise ValueError("Not enough coins!")

        # Use free coins first
        if amount <= self.free_coins:
            self.free_coins -= amount
        else:
            remaining = amount - self.free_coins
            self.free_coins = 0

            # Use subscribed coins next
            if remaining <= self.subscribed_coins:
                self.subscribed_coins -= remaining
            else:
                remaining -= self.subscribed_coins
                self.subscribed_coins = 0

                # Finally, use bought coins
                self.bought_coins -= remaining

        return self.save()


    def add_bought_coins(self, amount):
        """Add coins to the user's bought_coins balance."""
        self.bought_coins += amount

        return self.save()

    def reset_subscribed_coins(self, plan):
        """Reset the subscribed coins at the end of a billing cycle or set it to a specific amount."""
        self.subscribed_coins = plan["metadata"]["coins"]

        return self.save()