from monstagpt.app import create_celery_app
import stripe
import datetime
from lib.custom_logging_handler import send_slack_message
import os
from monstagpt.extensions import db
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.billing.models.invoice import Invoice
from monstagpt.blueprints.billing.models.subscription import Subscription
from monstagpt.blueprints.insights_api.models.update_keys import update_subscription_keys

celery = create_celery_app()
slack_critical_webhook_url = os.getenv("SLACK_CRITICAL_WEBHOOK_URL")


def get_plan_name_from_price_id(price_id,pricing_data):
    try:
        index = pricing_data["price_id"].index(price_id)
        return pricing_data["tiers"][index]
    except ValueError:
        # This block handles the case where price_id is not found
        return "Unknown plan"

def get_coins_by_price_id(price_id, pricing_data):
    try:
        index = pricing_data["price_id"].index(price_id)
        return pricing_data["coins"][index]
    except ValueError:
        # This block handles the case where price_id is not found
        return "0"
    
def get_plan_weight_from_name(plan_name, pricing_data):
    try:
        index = pricing_data["tiers"].index(plan_name)
        return pricing_data["plan_weight"][index]
    except ValueError:
        # This block handles the case where price_id is not found
        return "0"


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


@celery.task(queue='queue1')
def handle_session_complete(session,pricing_data,SLACK_GENERAL_WEBHOOK_URL):
    print('*** HANDLE SESSION COMPLETE HAS TRIGGERED ***')
    customer_id = session['customer']
    subscription_expiry = session['expires_at']
    invoice = session['invoice']
    purchase_type = session['mode'] # can be subscription or maybe purchase, find out
    payment_status = session['payment_status'] # shows paid for succesful payment, but check failed.
    subscription_id = session['subscription']
    line_items = stripe.checkout.Session.list_line_items(session['id'])
    subscription_bought = line_items['data'][0]['price']['id']

    print(f'{customer_id} purchased {subscription_bought}')
    print(f'payment_status: {payment_status}')
    print('here is the invoice:')
    print(invoice)
    plan_id = line_items['data'][0]['price']['id']
    plan = get_plan_name_from_price_id(plan_id,pricing_data)
    coins = get_coins_by_price_id(plan_id,pricing_data)
    u = User.query.filter_by(customer_id=customer_id).first()
    u.bought_coins = coins
    u.save()
    return None

@celery.task(queue='queue1')
def handle_subscription_update(session,pricing_data,SLACK_GENERAL_WEBHOOK_URL):
    print('*** HANDLE SUBSCRIPTION UPDATE HAS TRIGGERED ***')
    subscription_id = session['id']
    customer_id = session['customer']
    price_id = session['plan']['id']
    plan = get_plan_name_from_price_id(session['plan']['id'],pricing_data)
    u = User.query.filter_by(customer_id=customer_id).first()

    if not u:
        print(f"No user found with customer ID {customer_id}")
        u.customer_id = id
        u.save()
        return None
    
    sub = Subscription.query.filter_by(subscription_id=subscription_id).first()
    if not sub:
         # if it's the customers first attempt at buying, then the subscription id won't exist in the db yet
        print(f"No subscription found with ID {subscription_id}")
        print('Creating a new subsription')
        if not u.subscription:
            u.subscription = Subscription(user_id=u.id,customer_id=u.customer_id)
        u.subscription.subscription_id = subscription_id
        plan = get_plan_name_from_price_id(session['plan']['id'],pricing_data)
        u.subscription.plan = plan
        u.subscription.subscription_started = session['current_period_start']
        u.subscription.subscription_ends = session['current_period_end']
        u.subscription.status = 'active'
        u.subscribed_coins = get_coins_by_price_id(session['plan']['id'],pricing_data)
        u.save()

        # Send slack message to say customer bought a new subscription
        slack_message = f"""User *{u.email}* just bought subscription *{plan}*. Make sure
        to give them the approproate insights api key and S3 access."""
        send_slack_message(SLACK_GENERAL_WEBHOOK_URL, slack_message)
        return  None
    
    # Check if the user is switching plans and give an approproate number of coins
    if u.subscription.plan != plan:
        current_plan_weight = get_plan_weight_from_name(u.subscription.plan,pricing_data)
        new_plan_weight = get_plan_weight_from_name(plan,pricing_data)

        if int(new_plan_weight) > int(current_plan_weight):
            u.subscribed_coins = int(new_plan_weight)

        # Send slack message to say customer switched plans
        slack_message = f"""User *{u.email}* just Switched from plan *{u.subscription.plan}* to *{plan}*. 
        Their subscription changes on on {datetime.datetime.utcfromtimestamp(session['current_period_end']).strftime('%Y-%m-%d %H:%M:%S')}. 
        Rember to change their insights api key and S3 access as appropriate at this time."""
        send_slack_message(SLACK_GENERAL_WEBHOOK_URL, slack_message)

    if session.get('cancel_at_period_end'):
        print("Subscription will be canceled at the end of the billing period:", session['id'])
        sub.status = 'pending_cancellation'
        sub.subscription_ends = session.get('current_period_end')

        # Send slack message to say customer cancelled, when it ends and why
        slack_message = f"""User *{u.email}* just cancelled their subscription. Their subscription expires on
        {datetime.datetime.utcfromtimestamp(session['current_period_end']).strftime('%Y-%m-%d %H:%M:%S')}. Rember 
        to delete their insights api key and remove S3 access at this time. They gave these reasons for cancelling:
        {session['cancellation_details']}"""

        send_slack_message(SLACK_GENERAL_WEBHOOK_URL, slack_message)
       
    elif 'cancel_at_period_end' in session and not session.get('cancel_at_period_end'):
        print('customer is uncancelling their plan')
        # Check to see if a customer is uncancelling a plan
        if sub.status == 'pending_cancellation':
            # Send slack message to say customer uncancelled
            slack_message = f"""User *{u.email}* just undid the cancellation of their subscription. Make sure that
            they get to keep thir insights api key and S3 access."""
            send_slack_message(SLACK_GENERAL_WEBHOOK_URL, slack_message)
        sub.status = 'active'
        sub.plan_id = price_id
        sub.subscription_ends = session['current_period_end']
    sub.save()

    start_date = session['current_period_start']
    end_date = session['current_period_end']
    # Now try and get the insights api keys and save
    start_date_ymd = datetime.datetime.fromtimestamp(start_date).strftime('%Y-%m-%d')
    end_date_ymd = datetime.datetime.fromtimestamp(end_date).strftime('%Y-%m-%d')
    insights_key = update_subscription_keys(u.email,plan,start_date_ymd,end_date_ymd)
    return None


@celery.task(queue='queue1')
def handle_customer_update(customer,pricing_data,SLACK_GENERAL_WEBHOOK_URL):
    print('*** HANDLE CUSTOMER UPDATE HAS TRIGGERED ***')
    print("Customer updated:")
    name = customer['name']
    id = customer['id']
    email = customer['email']
    print(f'name:{name},id:{id},email:{email}')
    # check to see if the customer_id is in the db
    u = User.query.filter(User.customer_id == id).first()
    # if the customer_id is not present then update the user with the customer id.
    if not u:
        u = User.find_by_identity(email)
        u.customer_id = id
        u.save()

@celery.task(queue='queue1')
def handle_payment_failed(session,pricing_data,SLACK_GENERAL_WEBHOOK_URL):
    print('*** HANDLE PAYMENT FAILED HAS TRIGGERED ***')
    print(session)
    customer_id = session['customer']
    subscription_id = session['subscription']
    invoice_id = session['id']
    print(f"Payment failed for invoice:{invoice_id}")
    print("Customer ID:", customer_id)
    print("Subscription ID:", subscription_id)
    print("atteempt count:",session['attempt_count'])
    sub = Subscription.query.filter_by(subscription_id=subscription_id).first()
    if not sub:
        # if it's the customers first attempt at buying, then the subscription id won't exist in the db yet
        print(f"No subscription found with ID {subscription_id}")
        return  None
    sub.status = 'payment_failed'
    sub.plan = 'Free'
    sub.save()
    

@celery.task(queue='queue1')
def handle_payment_succeeded(invoice,pricing_data,SLACK_GENERAL_WEBHOOK_URL):
    print("Payment succeeded for invoice:", invoice['id'])
    if 'subscription' in invoice and invoice['subscription']:
        handle_subscription_payment(invoice,pricing_data,SLACK_GENERAL_WEBHOOK_URL)
    else:
        handle_one_time_payment(invoice,pricing_data)


def handle_subscription_payment(session,pricing_data,SLACK_GENERAL_WEBHOOK_URL):
    print('*** HANDLE SUBSCRIPTIO  PAYMENT HAS TRIGGERED ***')
    subscription_id = session['subscription']
    customer_id = session['customer']
    price_id = session['lines']['data'][-1]['plan']['id']
    period_end = session['lines']['data'][0]['period']['end']
    period_start = session['lines']['data'][0]['period']['start']
    print("Subscription payment succeeded for subscription:", subscription_id)
    print(subscription_id, 'active')
    u = User.query.filter(User.customer_id == customer_id).first()
    if not u:
        slack_message = f"""customer *{customer_id}* *{session['email']} *just signed 
            up to subscription {subscription_id} but customer not found in db. """
        send_slack_message(slack_critical_webhook_url, slack_message)
        return ('no user found')
    
    # Fetch the subscription based on the subscription_id
    subscription = Subscription.query.filter_by(subscription_id=subscription_id).first()
    if subscription:
        
        # Send slack message to say customer switched plans
        slack_message = f"""User *{u.email}* just Switched from plan *{u.subscription.plan}* to *{get_plan_name_from_price_id(price_id,pricing_data)}*.
        Their subscription changes on on {datetime.datetime.utcfromtimestamp(period_end).strftime('%Y-%m-%d %H:%M:%S')}. 
        Rember to change their insights api key and S3 access as appropriate at this time."""
        send_slack_message(SLACK_GENERAL_WEBHOOK_URL, slack_message)

        # Update existing subscription
        u.subscription.plan = get_plan_name_from_price_id(price_id,pricing_data)
        u.subscription.subscription_ends = period_end
        u.subscription.subscription_started = period_start
        u.subscription.status = 'active'
        u.subscribed_coins = get_coins_by_price_id(price_id,pricing_data)
        u.save()

    else:
        # Create a new subscription instance
        print('Creating a new subsription')
        subscription = Subscription(
            user_id = u.id,
            customer_id = u.customer_id,
            subscription_id=subscription_id,
            plan = get_plan_name_from_price_id(price_id,price_id),
            subscription_ends = period_end,
            subscription_started = period_start,
            subscribed_coins = get_coins_by_price_id(price_id,pricing_data),
            status = 'active',
        )
        db.session.add(subscription)
        # Send slack message to say customer bought a new subscription
        slack_message = f"""User *{u.email}* just bought subscription *{get_plan_name_from_price_id(price_id,pricing_data)}*. Make sure
        to give them the approproate insights api key and S3 access."""
        send_slack_message(slack_critical_webhook_url, slack_message)

    # Now create an invoice
    invoice = Invoice(
        user_id = u.id,
        plan = price_id,
        receipt_number = session['id'],
        description = get_plan_name_from_price_id(price_id,pricing_data),
        period_start_on = datetime.datetime.utcfromtimestamp(period_start).strftime('%Y-%m-%d'),
        period_end_on = datetime.datetime.utcfromtimestamp(period_end).strftime('%Y-%m-%d'),
        currency = session['currency'],
        paid = session['paid'],
        total = session['amount_paid'],
        url = session['hosted_invoice_url']
    )
    db.session.add(invoice)

    # Commit changes to the database
    db.session.commit()
    plan_name = get_plan_name_from_price_id(price_id,pricing_data)
    start_date_ymd = datetime.datetime.fromtimestamp(period_start).strftime('%Y-%m-%d')
    end_date_ymd = datetime.datetime.fromtimestamp(period_end).strftime('%Y-%m-%d')
    # Now try and get the insights api keys and save
    insights_key = update_subscription_keys(u.email,plan_name,start_date_ymd,end_date_ymd)

    return None



def handle_one_time_payment(invoice):
    print('*** HANDLE ONE TIME PAYMENT HAS TRIGGERED ***')
    print("One-time payment succeeded for invoice:", invoice['id'])
    # Implement logic specific to one-time payments
    # Example: Update an order status, trigger product delivery, etc.
    product_description = invoice['lines']['data'][0]['description']
    print(invoice['id'], 'paid', product_description)