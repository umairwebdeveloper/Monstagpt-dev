from flask import Blueprint
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import jsonify
from flask_login import current_user
from flask_login import login_required
from sqlalchemy import text
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import or_
from sqlalchemy import desc
from sqlalchemy.orm import Session
from monstagpt.extensions import db

from monstagpt.blueprints.admin.forms import BulkDeleteForm
from monstagpt.blueprints.admin.forms import CouponForm
from monstagpt.blueprints.admin.forms import SearchForm
from monstagpt.blueprints.admin.forms import UserCancelSubscriptionForm
from monstagpt.blueprints.admin.forms import UserForm
from monstagpt.blueprints.admin.forms import ItemForm
from monstagpt.blueprints.admin.forms import GPTInstructionsForm
from monstagpt.blueprints.admin.forms import AllowSignupsForm
from monstagpt.blueprints.admin.forms import RateForm
from monstagpt.blueprints.admin.models import Dashboard
from monstagpt.blueprints.billing.decorators import handle_stripe_exceptions
from monstagpt.blueprints.billing.models.coupon import Coupon
from monstagpt.blueprints.billing.models.invoice import Invoice
from monstagpt.blueprints.gpt.models.gpt import Gpt
from monstagpt.blueprints.billing.models.subscription import Subscription
from monstagpt.blueprints.user.decorators import role_required
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.gpt.models.suggested_questions import Suggested
from monstagpt.blueprints.admin.models import Settings
from monstagpt.blueprints.stripe_payments.models import ProductCatalog

admin = Blueprint(
    "admin", __name__, template_folder="templates", url_prefix="/admin"
)


@admin.before_request
@login_required
@role_required("admin")
def before_request():
    """Protect all of the admin endpoints."""
    pass


# Dashboard -------------------------------------------------------------------
@admin.route("", methods=["GET", "POST"])
def dashboard():
    group_and_count_plans = Dashboard.group_and_count_plans()
    group_and_count_coupons = Dashboard.group_and_count_coupons()
    group_and_count_users = Dashboard.group_and_count_users()
    group_and_count_costs = Dashboard.group_and_count_cost()
    user_costs = Dashboard.get_user_costs_for_current_month()
    print('****** costs *******')
    print(user_costs)

    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    last_month_date = today - relativedelta(months=1)
    last_month = last_month_date.month
    last_year = last_month_date.year

    form = ItemForm()
    item_list = Suggested.query.order_by(Suggested.order).all()

    allow_signin = Settings.query.first()
    allow_signups_form = AllowSignupsForm(obj=allow_signin)
    
    if allow_signups_form.validate_on_submit():
        print('yo')
        setting = Settings.query.get(1)
        if setting:
            print(f'settings before update: {setting}')

            # Assuming you want to update some fields in the 'setting' object
            setting.allow_signups = request.form.get("allow_signup")         
            print(f'sadfas: {request.form.get("allow_signup")}')
            # Add the object to the session and commit the session to save changes to the database
            allow_signups_form.populate_obj(setting)
            setting.save()

            print(f'settings after update: {setting}')
        else:
            print("Setting not found")

    return render_template(
        "admin/page/dashboard.html",
        group_and_count_plans=group_and_count_plans,
        group_and_count_coupons=group_and_count_coupons,
        group_and_count_users=group_and_count_users,
        costs=group_and_count_costs,
        current_month=current_month, 
        current_year_value=current_year, 
        last_month=last_month, 
        last_year=last_year,
        user_costs=user_costs,
        item_list=item_list,
        form=form,
        allow_signups_form = allow_signups_form
    )


# Users -----------------------------------------------------------------------
@admin.get("/users", defaults={"page": 1})
@admin.get("/users/page/<int:page>")
def users(page):
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    sort_by = User.sort_by(
        request.args.get("sort", "created_on"),
        request.args.get("direction", "desc"),
    )
    order_values = "{0} {1}".format(sort_by[0], sort_by[1])

    paginated_users = (
        User.query.filter(User.search(request.args.get("q", text(""))))
        .order_by(User.role.asc(), User.customer_id, text(order_values))
        .paginate(page=page, per_page=50)
    )

    return render_template(
        "admin/user/index.html",
        form=search_form,
        bulk_form=bulk_form,
        users=paginated_users,
    )


@admin.route("/users/edit/<int:id>", methods=["GET", "POST"])
def users_edit(id):
    user = User.query.get(id)
    form = UserForm(obj=user)

    last_question_on = Gpt.query.filter_by(user_id=id).order_by(desc(Gpt.created_on)).first()

    if not last_question_on:
        last_question_on = None
    else:
        last_question_on = last_question_on.created_on
        
    if current_user.subscription:
        coupon = Coupon.query.filter(
            Coupon.code == current_user.subscription.coupon
        ).first()
    else:
        coupon = None

    if form.validate_on_submit():
        if User.is_last_admin(
            user, request.form.get("role"), request.form.get("active")
        ):
            flash("You are the last admin, you cannot do that.", "error")
            return redirect(url_for("admin.users"))

        form.populate_obj(user)

        if not user.username:
            user.username = None

        user.save()

        flash("User has been saved successfully.", "success")
        return redirect(url_for("admin.users"))

    return render_template(
        "admin/user/edit.html", form=form, user=user, coupon=coupon, last_question_on = last_question_on
    )


@admin.post("/users/bulk_delete")
def users_bulk_delete():
    form = BulkDeleteForm()

    if form.validate_on_submit():
        ids = User.get_bulk_action_ids(
            request.form.get("scope"),
            request.form.getlist("bulk_ids"),
            omit_ids=[current_user.id],
            query=request.args.get("q", text("")),
        )

        # Prevent circular imports.
        from monstagpt.blueprints.billing.tasks import delete_users

        delete_users.delay(ids)

        flash(
            "{0} user(s) were scheduled to be deleted.".format(len(ids)),
            "success",
        )
    else:
        flash("No users were deleted, something went wrong.", "error")

    return redirect(url_for("admin.users"))


@admin.post("/users/cancel_subscription")
def users_cancel_subscription():
    form = UserCancelSubscriptionForm()

    if form.validate_on_submit():
        user = User.query.get(request.form.get("id"))

        if user:
            subscription = Subscription()
            if subscription.cancel(user):
                flash(
                    "Subscription has been cancelled for {0}.".format(
                        user.name
                    ),
                    "success",
                )
        else:
            flash(
                "No subscription was cancelled, something went wrong.", "error"
            )

    return redirect(url_for("admin.users"))


# Coupons ---------------------------------------------------------------------
@admin.get("/coupons", defaults={"page": 1})
@admin.get("/coupons/page/<int:page>")
def coupons(page):
    search_form = SearchForm()
    bulk_form = BulkDeleteForm()

    sort_by = Coupon.sort_by(
        request.args.get("sort", "created_on"),
        request.args.get("direction", "desc"),
    )
    order_values = "{0} {1}".format(sort_by[0], sort_by[1])

    paginated_coupons = (
        Coupon.query.filter(Coupon.search(request.args.get("q", text(""))))
        .order_by(text(order_values))
        .paginate(page=page, per_page=50)
    )

    return render_template(
        "admin/coupon/index.html",
        form=search_form,
        bulk_form=bulk_form,
        coupons=paginated_coupons,
    )


@admin.route("/coupons/new", methods=["GET", "POST"])
@handle_stripe_exceptions
def coupons_new():
    coupon = Coupon()
    form = CouponForm(obj=coupon)

    if form.validate_on_submit():
        form.populate_obj(coupon)

        params = {
            "code": coupon.code,
            "duration": coupon.duration,
            "percent_off": coupon.percent_off,
            "amount_off": coupon.amount_off,
            "currency": coupon.currency,
            "redeem_by": coupon.redeem_by,
            "max_redemptions": coupon.max_redemptions,
            "duration_in_months": coupon.duration_in_months,
        }

        if Coupon.create(params):
            flash("Coupon has been created successfully.", "success")
            return redirect(url_for("admin.coupons"))

    return render_template("admin/coupon/new.html", form=form, coupon=coupon)


@admin.post("/coupons/bulk_delete")
def coupons_bulk_delete():
    form = BulkDeleteForm()

    if form.validate_on_submit():
        ids = Coupon.get_bulk_action_ids(
            request.form.get("scope"),
            request.form.getlist("bulk_ids"),
            query=request.args.get("q", text("")),
        )

        # Prevent circular imports.
        from monstagpt.blueprints.billing.tasks import delete_coupons

        delete_coupons.delay(ids)

        flash(
            "{0} coupons(s) were scheduled to be deleted.".format(len(ids)),
            "success",
        )
    else:
        flash("No coupons were deleted, something went wrong.", "error")

    return redirect(url_for("admin.coupons"))


# Invoices --------------------------------------------------------------------
@admin.get("/invoices", defaults={"page": 1})
@admin.get("/invoices/page/<int:page>")
def invoices(page):
    search_form = SearchForm()

    sort_by = Invoice.sort_by(
        request.args.get("sort", "created_on"),
        request.args.get("direction", "desc"),
    )
    order_values = "invoices.{0} {1}".format(sort_by[0], sort_by[1])

    paginated_invoices = (
        Invoice.query.join(User)
        .filter(Invoice.search(request.args.get("q", text(""))))
        .order_by(text(order_values))
        .paginate(page=page, per_page=50)
    )

    return render_template(
        "admin/invoice/index.html",
        form=search_form,
        invoices=paginated_invoices,
    )


# Show gpt history
@admin.get("/gpt_history", defaults={"page": 1})
@admin.get("/gpt_history/page<int:page>")
def gpt_history(page):
    search_form = SearchForm()
    paginated_questions = (
        # //Gpt.query.filter(Gpt.user_id == current_user.id)
        Gpt.query.filter(Gpt.search(request.args.get("q", text(""))))
        .order_by(Gpt.created_on.desc())
        .paginate(page=page, per_page=20)
    )
    return render_template("admin/gpt/index.html", form=search_form, questions=paginated_questions)

# @admin.get("/gpt_history", defaults={"page": 1})
# @admin.get("/gpt_history/page<int:page>")
# def gpt_history(page):
#     search_form = SearchForm()
#     search_query = request.args.get("q", "").strip()

#     query = Gpt.query

#     if search_query:
#         search = "%{0}%".format(search_query)
#         subquery = User.query.with_entities(User.id).filter(User.email.ilike(search)).subquery()
#         query = query.filter(Gpt.user_id.in_(subquery))
#         print('***query')
#         print(str(query.statement.compile(compile_kwargs={"literal_binds": True})))


#     paginated_questions = query.order_by(Gpt.created_on.desc()).paginate(page=page, per_page=20)
#     return render_template("admin/gpt/index.html", form=search_form, questions=paginated_questions)


@admin.get("/reset/<identity>")
def reset_id(identity):
    from lib.security import sign_token
    u = User.find_by_identity(identity)
    reset_token = sign_token(u.email)
    return reset_token
    

@admin.route("/suggested/view_list", methods=['GET', 'POST'])
def view_list():
    form = ItemForm()
    item_list = Suggested.query.order_by(Suggested.order).all()
    return render_template('admin/gpt/suggested_questions.html', item_list=item_list,form=form)

@admin.route('/suggested/add', methods=['POST'])
def add_item():
    name = request.form.get('name')
    order = Suggested.query.count() + 1
    item = Suggested(question=name, order=order)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))

@admin.route('/suggested/update/<int:item_id>', methods=['GET','POST'])
def update_item(item_id):
    new_name = request.form.get('new_name')
    item = Suggested.query.get(item_id)
    item.question = new_name
    db.session.commit()
    return redirect(url_for('admin.dashboard'))

@admin.route('/suggested/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Suggested.query.get(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('admin.dashboard'))

@admin.route('/suggested/reorder', methods=['POST'])
def reorder_items():
    # Retrieve the new order of item IDs from the request data
    new_order = request.json.get('order')

    # Retrieve items from the database based on the order
    items = Suggested.query.filter(Suggested.id.in_(new_order)).all()

    # Create a dictionary to map item IDs to their new order positions
    new_order_map = {item.id: new_order.index(str(item.id)) for item in items}

    # Update the order of items in the database
    for item in items:
        item.list_order = new_order_map[item.id]

    # Commit the changes to the database
    db.session.commit()

    # Return a JSON response to indicate success
    return jsonify({'message': 'Items reordered successfully'})

@admin.route('/instructions_update', methods=["GET","POST"])
def instructions_update():
        with open("monstagpt/blueprints/gpt/templates/gpt/instructions/instructions.txt", "r") as f: 
            contents = f.read() 
        form = GPTInstructionsForm(instructions=contents)

        if form.validate_on_submit():
            new_instructions = request.form.get('instructions')
            with open("monstagpt/blueprints/gpt/templates/gpt/instructions/instructions.txt", "w") as f:
                f.write(new_instructions)
            flash("Instructions updated succesfully!", "success")
            return redirect(url_for("admin.dashboard"))

        return render_template('admin/page/instructions.html',form=form)

@admin.route('/manage_tiers', methods=['GET', 'POST'])
def manage_tiers():
    form = RateForm()
    if form.validate_on_submit():
        tier = form.tier.data
        rate_limit_seconds = form.rate_limit_seconds.data
        
        try:
            ProductCatalog.update_tier(tier, rate_limit_seconds)
            flash('Tier added/updated successfully', 'success')
            return redirect(url_for('stripe_payments.manage_tiers'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    
    tiers = ProductCatalog.query.order_by(ProductCatalog.id).all()
    return render_template('admin/page/manage_tiers.html', form=form, tiers=tiers)

@admin.route('/tier/edit/<int:tier_id>', methods=['GET', 'POST'])
def edit_tier(tier_id):
    tier_entry = ProductCatalog.query.get_or_404(tier_id)
    form = RateForm(obj=tier_entry)
    
    if form.validate_on_submit():
        tier_entry.tier = form.tier.data
        tier_entry.rate_limit_seconds = form.rate_limit_seconds.data
        
        try:
            db.session.commit()
            flash('Tier updated successfully', 'success')
            return redirect(url_for('admin.manage_tiers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    
    return render_template('admin/page/edit_tier.html', form=form, tier=tier_entry)