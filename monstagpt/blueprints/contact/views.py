from flask import Blueprint
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_login import current_user
from flask_login import login_required
from flask import current_app
from lib.custom_logging_handler import send_slack_message

from monstagpt.blueprints.contact.forms import ContactForm

contact = Blueprint("contact", __name__, template_folder="templates")


@contact.route("/contact", methods=["GET", "POST"])
def index():
    slack_support_webhook_url = current_app.config.get("SLACK_SUPPORT_WEBHOOK_URL")
    print(f'***** SLACK SUPPORT URL: {slack_support_webhook_url} *******')

    # Pre-populate the email field if the user is signed in.
    form = ContactForm(obj=current_user)
    recipient = current_app.config.get("MAIL_DEFAULT_TO")

    if form.validate_on_submit():
        # This prevents circular imports.
        from monstagpt.blueprints.contact.tasks import deliver_contact_email

        deliver_contact_email.delay(
            request.form.get("email"),recipient, request.form.get("message"),slack_support_webhook_url
        )

        flash("Thanks, expect a response shortly.", "success")
        return redirect(url_for("contact.index"))

    return render_template("contact/index.html", form=form)

@contact.route('/free_tokens', methods=['GET','POST'])
@login_required
def free_tokens():
    if not current_user.requested_tokens:
        flash("You've already requested free tokens, please be patient.", "success")
        return redirect(url_for("user.settings"))

    slack_support_webhook_url = current_app.config.get("SLACK_SUPPORT_WEBHOOK_URL")
    form = ContactForm(obj=current_user)
    recipient = current_app.config.get("MAIL_DEFAULT_TO")
    
    if form.validate_on_submit():

        # This prevents circular imports.
        from monstagpt.blueprints.contact.tasks import deliver_free_tokens_email

        deliver_free_tokens_email.delay(
            current_user.email,recipient, request.form.get('message'),slack_support_webhook_url
        )

        flash("We've received your request for tokens and will review shortly.", "success")
        return redirect(url_for("user.settings"))

    return render_template("contact/request_tokens.html", form=form)
