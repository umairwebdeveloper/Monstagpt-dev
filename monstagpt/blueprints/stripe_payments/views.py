from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import current_app
from flask_login import current_user
from flask_login import login_required
from lib.util_json import render_json
import stripe
import os
from config import settings
from monstagpt.extensions import db
from monstagpt.blueprints.stripe_payments.models import ProductCatalog
from monstagpt.blueprints.stripe_payments.pricing_data import pricing_data

from monstagpt.extensions import csrf
stripe_payments = Blueprint('stripe_payments', __name__, template_folder='templates', url_prefix='/stripe')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@stripe_payments.route('/test')
@login_required
def test():
    if not current_user.has_seen_pricing:
        current_user.has_seen_pricing = True
        db.session.commit()
    return render_template(
        "stripe_payments/pricing_bs.html" ,plans=settings.STRIPE_PLANS,pricing_data=pricing_data)

@stripe_payments.route('/test1')
@login_required
def test1():
    return render_template(
        "stripe_payments/pricing_bs_1.html" ,pricing_data=pricing_data)

@stripe_payments.route('/buy_gpt',methods=['POST'])
@login_required
def buy_gpt():
    data = request.get_json()
    print(f'DATA: {data}')
    # Next up, add this to the other buttons, and make a lookup for the price and mode
    # then make a check for customer id and email. cant send both so if they have an id, dont pass email.
    plan_name = data['plan']
    index = pricing_data["tiers"].index(plan_name)
    price_id = pricing_data["price_id"][index]
    mode = pricing_data["mode"][index]

    customer_email = None
    customer = None
    # If the user doesn't have a customer id, create one before proceeding.
    if not current_user.customer_id:
        new_customer = stripe.Customer.create(
        email=current_user.email,
        )
        current_user.customer_id = new_customer['id']
        db.session.commit()
        
    print(f'customer_id = {current_user.customer_id}')
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode=mode,
        customer = current_user.customer_id, # The existing customer id. They might go for multiple subscriptions or one time payments so make sure
        # to look this up from the db
        success_url=url_for('stripe_payments.thanks', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('user.settings', _external=True),
    )
    return {
        'checkout_session_id': session['id'], 
        'checkout_public_key': os.getenv('STRIPE_PUBLISHABLE_KEY')
    }


@stripe_payments.route('/create-customer-portal-session')
@login_required
def stripe_customer_portal():
    customer_id = current_user.customer_id
    try:
        session = stripe.billing_portal.Session.create(
        customer = customer_id,
        return_url =url_for("user.settings", _external=True),
        )
        return redirect(session.url)
    except stripe.error.StripeError as e:
        print("Failed to create session:", e)
        return "An error occurred, please try again later.", 500

@stripe_payments.route('/thanks')
@login_required
def thanks():
    flash("Thanks for your purchase", "success")
    return redirect(url_for("user.settings"))

@stripe_payments.route('/stripe_webhook', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    print('Webhook called')
    if request.content_length > 1024*1024:
        print('request too big')
        ConnectionAbortedError(400)
    payload = request.get_data()
    sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = os.getenv('STRIPE_ENDPOINT_SECRET',None)
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        #invalid payload
        print('invalid payload')
        return {}, 400
    except stripe.error.SignatureVerificationError as e:
        #invalid signature
        print('invalid signature')
        return {}, 400
    
    pricing_data = current_app.config.get("PRICING_DATA")
    SLACK_GENERAL_WEBHOOK_URL = current_app.config.get("SLACK_GENERAL_WEBHOOK_URL")
    # Handle cthe checkout.session.completed event
    if event['type'] == 'customer.updated':
        from monstagpt.blueprints.stripe_payments.tasks import handle_customer_update
        handle_customer_update.delay(event['data']['object'],pricing_data,SLACK_GENERAL_WEBHOOK_URL)
    elif event['type'] == 'customer.subscription.updated':
        from monstagpt.blueprints.stripe_payments.tasks import handle_subscription_update
        handle_subscription_update.delay(event['data']['object'],pricing_data,SLACK_GENERAL_WEBHOOK_URL)
    elif event['type'] == 'invoice.payment_failed':
        from monstagpt.blueprints.stripe_payments.tasks import handle_payment_failed
        handle_payment_failed.delay(event['data']['object'],pricing_data,SLACK_GENERAL_WEBHOOK_URL)
    elif event['type'] == 'invoice.payment_succeeded':
        from monstagpt.blueprints.stripe_payments.tasks import handle_payment_succeeded
        handle_payment_succeeded.delay(event['data']['object'],pricing_data,SLACK_GENERAL_WEBHOOK_URL)
    elif event['type'] == 'checkout.session.completed':
        from monstagpt.blueprints.stripe_payments.tasks import handle_session_complete
        handle_session_complete.delay(event['data']['object'],pricing_data,SLACK_GENERAL_WEBHOOK_URL)
 
    return render_json(200, {"success": True})