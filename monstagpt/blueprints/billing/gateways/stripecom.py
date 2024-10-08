import datetime

import stripe

from config.settings import STRIPE_TRIAL_PERIOD_DAYS


class Event(object):
    @classmethod
    def retrieve(cls, event_id):
        """
        Retrieve an event, this is used to validate the event in attempt to
        protect us from potentially malicious events not sent from Stripe.

        API Documentation:
          https://stripe.com/docs/api#retrieve_event

        :param event_id: Stripe event id
        :type event_id: int
        :return: Stripe event
        """
        return stripe.Event.retrieve(event_id)


class Customer(object):
    @classmethod
    def create(cls, token=None, email=None):
        """
        Create a new customer.

        API Documentation:
          https://stripe.com/docs/api#create_customer

        :param token: Token returned by JavaScript
        :type token: str
        :param email: E-mail address of the customer
        :type email: str
        :return: Stripe customer
        """
        params = {"source": token, "email": email, "expand": ["sources"]}

        return stripe.Customer.create(**params)


class Charge(object):
    @classmethod
    def create(cls, customer_id=None, currency=None, amount=None):
        """
        Create a new charge.

        :param customer_id: Stripe customer id
        :type customer_id: int
        :param amount: Stripe currency
        :type amount: str
        :param amount: Amount in cents
        :type amount: int
        :return: Stripe charge
        """
        statement_descriptor = "MONSTAGPT TOKENS"

        # Stripe requires a minimum of 50 cents to create a charge, so if it's
        # below that let's return a charge-like object so that we can create
        # an invoice later on with this data.
        if amount < 50:
            return {
                "created": datetime.datetime.now().timestamp(),
                "receipt_number": "N/A",
                "currency": "N/A",
                "amount": 0,
                "statement_descriptor": statement_descriptor,
            }

        return stripe.Charge.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            statement_descriptor=statement_descriptor,
        )


class Coupon(object):
    @classmethod
    def create(
        cls,
        code=None,
        duration=None,
        amount_off=None,
        percent_off=None,
        currency=None,
        duration_in_months=None,
        max_redemptions=None,
        redeem_by=None,
    ):
        """
        Create a new coupon.

        API Documentation:
          https://stripe.com/docs/api#create_coupon

        :param code: Coupon code
        :param duration: How long the coupon will be in effect
        :type duration: str
        :param amount_off: Discount in a fixed amount
        :type amount_off: int
        :param percent_off: Discount based on percent off
        :type percent_off: int
        :param currency: 3 digit currency abbreviation
        :type currency: str
        :param duration_in_months: Number of months in effect
        :type duration_in_months: int
        :param max_redemptions: Max number of times it can be redeemed
        :type max_redemptions: int
        :param redeem_by: Redeemable by this date
        :type redeem_by: date
        :return: Stripe coupon
        """
        return stripe.Coupon.create(
            id=code,
            duration=duration,
            amount_off=amount_off,
            percent_off=percent_off,
            currency=currency,
            duration_in_months=duration_in_months,
            max_redemptions=max_redemptions,
            redeem_by=redeem_by,
        )

    @classmethod
    def delete(cls, id=None):
        """
        Delete an existing coupon.

        API Documentation:
          https://stripe.com/docs/api#delete_coupon

        :param id: Coupon code
        :return: Stripe coupon
        """
        coupon = stripe.Coupon.retrieve(id)
        return coupon.delete()


class Card(object):
    @classmethod
    def update(cls, customer_id, stripe_token=None):
        """
        Update an existing card through a customer.

        API Documentation:
          https://stripe.com/docs/api/python#update_card

        :param customer_id: Stripe customer id
        :type customer_id: int
        :param stripe_token: Stripe token
        :type stripe_token: str
        :return: Stripe customer
        """
        customer = stripe.Customer.modify(
            customer_id, source=stripe_token, expand=["sources"]
        )

        return customer


class Invoice(object):
    @classmethod
    def upcoming(cls, customer_id):
        """
        Retrieve an upcoming invoice item for a user.

        API Documentation:
          https://stripe.com/docs/api#retrieve_customer_invoice

        :param customer_id: Stripe customer id
        :type customer_id: int
        :return: Stripe invoice
        """
        return stripe.Invoice.upcoming(customer=customer_id)


class Subscription(object):
    @classmethod
    def create(cls, customer_id=None, coupon=None, plan=None):
        """
        Create a subscription for a customer.

        API Documentation:
          https://stripe.com/docs/api/python#create_subscription

        :param customer_id: Customer id
        :type customer_id: str
        :param coupon: Coupon code
        :type coupon: str
        :param plan: Plan identifier
        :type plan: str
        :return: Stripe subscription
        """
        params = {
            "customer": customer_id,
            "items": [{"plan": plan}],
            "trial_period_days": STRIPE_TRIAL_PERIOD_DAYS,
        }

        if coupon:
            params["coupon"] = coupon

        return stripe.Subscription.create(**params)

    @classmethod
    def update(cls, customer_id=None, coupon=None, plan=None):
        """
        Update an existing subscription.

        API Documentation:
          https://stripe.com/docs/api/python#update_subscription

        :param customer_id: Customer id
        :type customer_id: str
        :param coupon: Coupon code
        :type coupon: str
        :param plan: Plan identifier
        :type plan: str
        :return: Stripe subscription
        """
        customer = stripe.Customer.retrieve(
            customer_id, expand=["subscriptions"]
        )
        subscription_id = customer.subscriptions.data[0].id
        subscription = customer.subscriptions.retrieve(subscription_id)

        subscription.plan = plan

        if coupon:
            subscription.coupon = coupon.upper()

        return subscription.save()

    @classmethod
    def cancel(cls, customer_id=None):
        """
        Cancel an existing subscription.

        API Documentation:
          https://stripe.com/docs/api#cancel_subscription

        :param customer_id: Stripe customer id
        :type customer_id: int
        :return: Stripe subscription object
        """
        customer = stripe.Customer.retrieve(
            customer_id, expand=["subscriptions"]
        )
        subscription_id = customer.subscriptions.data[0].id

        return customer.subscriptions.retrieve(subscription_id).delete()


class Product(object):
    @classmethod
    def retrieve(cls, plan):
        """
        Retrieve an existing product.

        API Documentation:
          https://stripe.com/docs/api#retrieve_product

        :param plan: Product identifier
        :type plan: str
        :return: Stripe product
        """
        try:
            return stripe.Product.retrieve(plan)
        except stripe.error.StripeError as e:
            print(e)


class Plan(object):
    @classmethod
    def retrieve(cls, plan):
        """
        Retrieve an existing plan.

        API Documentation:
          https://stripe.com/docs/api#retrieve_plan

        :param plan: Plan identifier
        :type plan: str
        :return: Stripe plan
        """
        try:
            return stripe.Plan.retrieve(plan)
        except stripe.error.StripeError as e:
            print(e)

    @classmethod
    def list(cls):
        """
        List all plans.

        API Documentation:
          https://stripe.com/docs/api#list_plans

        :return: Stripe plans
        """
        try:
            return stripe.Plan.list()
        except stripe.error.StripeError as e:
            print(e)

    @classmethod
    def create(
        cls,
        id=None,
        name=None,
        amount=None,
        currency=None,
        interval=None,
        interval_count=None,
        metadata=None,
        statement_descriptor=None,
    ):
        """
        Create a new plan.

        API Documentation:
          https://stripe.com/docs/api#create_plan

        :param id: Plan identifier
        :type id: str
        :param name: Plan name
        :type name: str
        :param amount: Amount in cents to charge or 0 for a free plan
        :type amount: int
        :param currency: 3 digit currency abbreviation
        :type currency: str
        :param interval: Billing frequency
        :type interval: str
        :param interval_count: Number of intervals between each bill
        :type interval_count: int
        :param metadata: Additional data to save with the plan
        :type metadata: dct
        :param statement_descriptor: Arbitrary string to appear on CC statement
        :type statement_descriptor: str
        :return: Stripe plan
        """
        try:
            product = {
                "name": name,
                "statement_descriptor": statement_descriptor,
            }

            return stripe.Plan.create(
                id=id,
                amount=amount,
                currency=currency,
                interval=interval,
                interval_count=interval_count,
                nickname=name,
                metadata=metadata,
                product=product,
            )
        except stripe.error.StripeError as e:
            print(e)

    @classmethod
    def update(
        cls, id=None, name=None, metadata=None, statement_descriptor=None
    ):
        """
        Update an existing plan.

        API Documentation:
          https://stripe.com/docs/api#update_plan

        :param id: Plan identifier
        :type id: str
        :param name: Plan name
        :type name: str
        :param metadata: Additional data to save with the plan
        :type metadata: dct
        :param statement_descriptor: Arbitrary string to appear on CC statement
        :type statement_descriptor: str
        :return: Stripe plan
        """
        try:
            plan = stripe.Plan.retrieve(id)
            plan.nickname = name
            plan.metadata = metadata
            product_id = plan.product
            updated_plan = plan.save()

            product = Product.retrieve(product_id)
            product.name = name
            product.statement_descriptor = statement_descriptor
            product.save()

            return updated_plan
        except stripe.error.StripeError as e:
            print(e)

    @classmethod
    def delete(cls, plan):
        """
        Delete an existing plan.

        API Documentation:
          https://stripe.com/docs/api#delete_plan

        :param plan: Plan identifier
        :type plan: str
        :return: Stripe plan object
        """
        try:
            plan = stripe.Plan.retrieve(plan)
            product_id = plan.product
            deleted_plan = plan.delete()

            product = Product.retrieve(product_id)
            product.delete()

            return deleted_plan
        except stripe.error.StripeError as e:
            print(e)
