from flask import Blueprint
from flask import current_app
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_babel import gettext as _
from flask_login import current_user
from flask_login import login_required
import datetime

from config import settings
from lib.util_json import render_json
from monstagpt.blueprints.billing.decorators import handle_stripe_exceptions
from monstagpt.blueprints.billing.decorators import subscription_required
from monstagpt.blueprints.user.decorators import confirmed_required
from monstagpt.blueprints.billing.forms import CancelSubscriptionForm
from monstagpt.blueprints.billing.forms import PaymentForm
from monstagpt.blueprints.billing.forms import SubscriptionForm
from monstagpt.blueprints.billing.forms import UpdateSubscriptionForm
from monstagpt.blueprints.billing.models.coupon import Coupon
from monstagpt.blueprints.billing.models.invoice import Invoice
from monstagpt.blueprints.billing.models.subscription import Subscription
from monstagpt.blueprints.gpt.decorators import subscription_required

billing = Blueprint(
    "billing",
    __name__,
    template_folder="../templates",
    url_prefix="/subscription",
)


@billing.get("/pricing")
def pricing():
    if current_user.is_authenticated and current_user.subscription:
        return redirect(url_for("billing.update"))

    form = UpdateSubscriptionForm()

    return render_template(
        "billing/pricing.html", form=form, plans=settings.STRIPE_PLANS
    )


@billing.post("/coupon_code")
@login_required
def coupon_code():
    code = request.form.get("coupon_code")

    if code is None:
        return render_json(422, {"error": "Coupon code cannot be processed."})

    coupon = Coupon.find_by_code(code)
    if coupon is None:
        return render_json(404, {"error": "Coupon code not found."})

    return render_json(200, {"data": coupon.to_json()})


@billing.route("/create", methods=["GET", "POST"])
@handle_stripe_exceptions
@login_required
@confirmed_required
def create():
    if current_user.subscription:
        flash(_("You already have an active subscription."), "info")
        return redirect(url_for("user.settings"))

    plan = request.args.get("plan")
    subscription_plan = Subscription.get_plan_by_id(plan)

    # Guard against an invalid or missing plan.
    if subscription_plan is None and request.method == "GET":
        flash(_("Sorry, that plan did not exist."), "error")
        return redirect(url_for("billing.pricing"))

    stripe_key = current_app.config.get("STRIPE_PUBLISHABLE_KEY")
    form = SubscriptionForm(stripe_key=stripe_key, plan=plan)

    if form.validate_on_submit():
        subscription = Subscription()
        created = subscription.create(
            user=current_user,
            name=request.form.get("name"),
            plan=request.form.get("plan"),
            coupon_code=request.form.get("coupon_code"),
            token=request.form.get("stripe_token"),
        )

        if created:
            flash(_("Awesome, thanks for subscribing!"), "success")
        else:
            flash(_("You must enable JavaScript for this request."), "warning")

        return redirect(url_for("user.settings"))

    return render_template(
        "billing/payment_method.html", form=form, plan=subscription_plan
    )


@billing.route("/update", methods=["GET", "POST"])
@handle_stripe_exceptions
@login_required
@subscription_required
def update():
    current_plan = current_user.subscription.plan
    active_plan = Subscription.get_plan_by_id(current_plan)
    new_plan = Subscription.get_new_plan(request.form.keys())

    plan = Subscription.get_plan_by_id(new_plan)

    # Guard against an invalid, missing or identical plan.
    is_same_plan = new_plan == active_plan["id"]
    if (
        (new_plan is not None and plan is None) or is_same_plan
    ) and request.method == "POST":
        return redirect(url_for("billing.update"))

    form = UpdateSubscriptionForm(coupon_code=current_user.subscription.coupon)

    if form.validate_on_submit():
        subscription = Subscription()
        updated = subscription.update(
            user=current_user,
            coupon_code=request.form.get("coupon_code"),
            plan=plan.get("id"),
        )

        if updated:
            flash(_("Your subscription has been updated."), "success")
            return redirect(url_for("user.settings"))
        else:
            flash(_("That coupon code is not valid."), "error")
            return redirect(url_for("billing.update"))

    return render_template(
        "billing/pricing.html",
        form=form,
        plans=settings.STRIPE_PLANS,
        active_plan=active_plan,
    )


@billing.route("/cancel", methods=["GET", "POST"])
@handle_stripe_exceptions
@login_required
def cancel():
    if not current_user.subscription:
        flash(_("You do not have an active subscription."), "error")
        return redirect(url_for("user.settings"))
    
    if current_user.subscription.cancelled:
        flash(_("You have alrady cancelled your subscription"), "error")
        return redirect(url_for("user.settings"))
    
    upcoming = Invoice.upcoming(current_user.customer_id)

    form = CancelSubscriptionForm()

    if form.validate_on_submit():
        upcoming = Invoice.upcoming(current_user.customer_id)
        subscription_end = upcoming['next_bill_on'].date() - datetime.timedelta(days=1)
        subscription = Subscription()
        cancelled = subscription.prepare_cancel(user=current_user,subscription_end = subscription_end)

        if cancelled:
            flash(
                _(
                    "Sorry to see you go, your subscription has been "
                    "cancelled."
                ),
                "success",
            )
            return redirect(url_for("user.settings"))

    return render_template("billing/cancel.html", form=form,bill=upcoming['next_bill_on'].date())

@billing.route('/prepare_cancel',methods=["GET"])
@login_required
def prepare_cancel():
    if not current_user.subscription:
        flash(_("You do not have an active subscription."), "error")
        return redirect(url_for("user.settings"))
    
    upcoming = Invoice.upcoming(current_user.customer_id)
    subscription_end = upcoming['next_bill_on'].date() - datetime.timedelta(days=1)
    subscription = Subscription()
    cancelled = subscription.prepare_cancel(user=current_user,subscription_end = subscription_end)
    flash('You have cancelled your subscription','info')
    return redirect(url_for("user.settings"))

@billing.route('/undo_cancel',methods=["GET"])
@login_required
def undo_cancel():
    if not current_user.subscription:
        flash(_("You do not have an active subscription."), "error")
        return redirect(url_for("user.settings"))
    
    subscription = Subscription()
    subscription.undo_cancel(user=current_user)
    flash('Cancellation undone, your subscription will remain active','success')
    return redirect(url_for("user.settings"))

@billing.route("/update_payment_method", methods=["GET", "POST"])
@handle_stripe_exceptions
@login_required
def update_payment_method():
    # if not current_user.credit_card:
    #     flash(_("You do not have a payment method on file."), "error")
    #     return redirect(url_for("user.settings"))

    active_plan = Subscription.get_plan_by_id(current_user.subscription.plan)

    card = current_user.credit_card
    stripe_key = current_app.config.get("STRIPE_PUBLISHABLE_KEY")
    form = SubscriptionForm(
        stripe_key=stripe_key, plan=active_plan
        # , name=current_user.name
    )

    if form.validate_on_submit():
        subscription = Subscription()
        updated = subscription.update_payment_method(
            user=current_user,
            credit_card=card,
            name=request.form.get("name"),
            token=request.form.get("stripe_token"),
        )

        if updated:
            flash(_("Your payment method has been updated."), "success")
        else:
            flash(_("You must enable JavaScript for this request."), "warning")

        return redirect(url_for("user.settings"))

    return render_template(
        "billing/payment_method.html",
        form=form,
        plan=active_plan,
        # card_last4=card.last4,
    )


@billing.get("/billing_details", defaults={"page": 1})
@billing.get("/billing_details/page/<int:page>")
@handle_stripe_exceptions
@login_required
def billing_details(page):
    paginated_invoices = (
        Invoice.query.filter(Invoice.user_id == current_user.id)
        .order_by(Invoice.created_on.desc())
        .paginate(page=page, per_page=12)
    )

    if current_user.subscription:
        upcoming = Invoice.upcoming(current_user.customer_id)
        coupon = Coupon.query.filter(
            Coupon.code == current_user.subscription.coupon
        ).first()
    else:
        upcoming = None
        coupon = None

    return render_template(
        "billing/billing_details.html",
        paginated_invoices=paginated_invoices,
        upcoming=upcoming,
        coupon=coupon,
    )


@billing.route("/purchase_coins", methods=["GET", "POST"])
@login_required
# @subscription_required
def purchase_coins():
    stripe_key = current_app.config.get("STRIPE_PUBLISHABLE_KEY")
    form = PaymentForm(stripe_key=stripe_key)

    if form.validate_on_submit():
        coin_bundles = current_app.config.get("COIN_BUNDLES")
        coin_bundles_form = int(request.form.get("coin_bundles"))

        bundle = next(
            (
                item
                for item in coin_bundles
                if item["coins"] == coin_bundles_form
            ),
            None,
        )

        if bundle is not None:
            invoice = Invoice()
            created = invoice.create(
                user=current_user,
                currency=current_app.config.get("STRIPE_CURRENCY"),
                amount=bundle.get("price_in_cents"),
                coins=coin_bundles_form,
                coupon=request.form.get("coupon_code"),
                token=request.form.get("stripe_token"),
            )

            if created:
                flash(
                    _(
                        "%(amount)s tokens have been added to your account.",
                        amount=coin_bundles_form,
                    ),
                    "success",
                )
            else:
                flash(
                    _("You must enable JavaScript for this request."),
                    "warning",
                )

            return redirect(url_for("user.settings"))

    return render_template("billing/purchase_coins.html", form=form)
