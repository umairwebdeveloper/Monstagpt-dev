from monstagpt.app import create_celery_app
from monstagpt.blueprints.billing.models.coupon import Coupon
from monstagpt.blueprints.billing.models.credit_card import CreditCard
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.billing.models.subscription import Subscription

celery = create_celery_app()


@celery.task(queue='queue1')
def mark_old_credit_cards():
    """
    Mark credit cards that are going to expire soon or have expired.

    :return: Result of updating the records
    """
    return None
    # return CreditCard.mark_old_credit_cards()


@celery.task(queue='queue1')
def expire_old_coupons():
    """
    Invalidate coupons that are past their redeem date.

    :return: Result of updating the records
    """
    return Coupon.expire_old_coupons()


@celery.task(queue='queue1')
def delete_users(ids):
    """
    Delete users and potentially cancel their subscription.

    :param ids: List of ids to be deleted
    :type ids: list
    :return: int
    """
    return User.bulk_delete(ids)


@celery.task(queue='queue1')
def delete_coupons(ids):
    """
    Delete coupons both on the payment gateway and locally.

    :param ids: List of ids to be deleted
    :type ids: list
    :return: int
    """
    return Coupon.bulk_delete(ids)

@celery.task(queue='queue1')
def cancel_expired_subscriptions():
    """
    Cancel and delete subscriptions that have been cancelled
    and reached the end of a billing cycle
    
    :return: Result of updating the records
    """
    return Subscription.cancel_all_expired_subscriptions()