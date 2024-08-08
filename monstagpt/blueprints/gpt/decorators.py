from functools import wraps

from flask import flash
from flask import redirect
from flask import url_for
from flask_login import current_user

def tokens_required(f):
    """
    Restrict access from users who have no coins.

    :return: Function
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.coins < 1:
            flash(
                "Sorry, you're out of tokens. You should buy more.", "warning"
            )
            return redirect(url_for("user.settings"))

        return f(*args, **kwargs)

    return decorated_function

def subscription_required(f):
    """
    Restrict access from users who have no subscription.

    :return: Function
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.subscription:
            flash(
                "Sorry, you need an active subscription to access this page.", "warning"
            )
            return redirect(url_for("billing.pricing"))

        return f(*args, **kwargs)

    return decorated_function