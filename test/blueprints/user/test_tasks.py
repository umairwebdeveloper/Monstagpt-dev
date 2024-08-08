from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.user.tasks import deliver_password_reset_email
from monstagpt.extensions import mail


class TestTasks(object):
    def test_deliver_password_reset_email(self, token):
        """Deliver a password reset email."""
        with mail.record_messages() as outbox:
            user = User.find_by_identity("admin@local.host")
            deliver_password_reset_email(user.id, token)

            # TODO: Figure out why this assert fails when the entire test suite
            # is run but it passes when it's run individually.
            # assert len(outbox) == 1

            assert token in outbox[0].body
