from monstagpt.blueprints.billing.models.subscription import Subscription
from monstagpt.blueprints.user.models import User


class TestUser(object):
    def test_serialize_token(self, token):
        """Token serializer serializes a token correctly."""
        assert token.count(".") == 2

    def test_find_by_token_token(self, token):
        """Token de-serializer de-serializes a token correctly."""
        user = User.find_by_token(token)
        assert user.email == "admin@local.host"

    def test_find_by_token_tampered(self, token):
        """Token de-serializer returns None when it's been tampered with."""
        user = User.find_by_token("{0}1337".format(token))
        assert user is None

    def test_subscribed_user_receives_more_coins(self, users):
        """Subscribed user receives more coins."""
        user = User.find_by_identity("admin@local.host")
        user.add_coins(Subscription.get_plan_by_id("bronze"))

        assert user.coins == 210
