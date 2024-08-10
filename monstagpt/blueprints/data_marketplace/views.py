from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import url_for
from flask_login import current_user
from flask_login import login_required

data_marketplace = Blueprint('data_marketplace', __name__, template_folder='templates',url_prefix='/data_marketplace')

@data_marketplace.before_request
@login_required
def before_request():
    """ Protect all of the api endpoints. """
    pass


@data_marketplace.route('/')
def index():
    if (not current_user.subscription) or (current_user.subscription.status == 'expired'):
        return redirect(url_for("stripe_payments.test", referer='data_marketplace'))
    else:
        return render_template(
            "data_marketplace/index.html")
    