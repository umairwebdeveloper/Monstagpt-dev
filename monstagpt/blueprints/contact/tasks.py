
from lib.flask_mailplus import send_template_message
from monstagpt.app import create_celery_app
from monstagpt.blueprints.user.models import User
from lib.custom_logging_handler import send_slack_message

celery = create_celery_app()
send_email = False

@celery.task(queue='queue1')
def deliver_contact_email(email,recipient, message, slack_url):
    """
    Send a contact e-mail.

    :param email: E-mail address of the visitor
    :type user_id: str
    :param message: E-mail message
    :type user_id: str
    :return: None
    """


    body_html = None
    with open("monstagpt/blueprints/contact/templates/contact/mail/index_html.txt", "r") as f: 
        contents = f.read() 
        body_html = contents.replace('{{custom_message}}', message)
        body_html = body_html.replace('{{user_email}}', email)


    body_text = None
    with open("monstagpt/blueprints/contact/templates/contact/mail/index_text.txt", "r") as f: 
        contents = f.read() 
        body_text = contents.replace('{{custom_message}}', message)
        body_text = body_text.replace('{{user_email}}', email)

    ctx = {"user_email": email, "message": message}

    # recipient=None,subject=None,body_text=None,body_html=None)
    if send_email:
        send_template_message(
            recipient = recipient,
            subject = 'Contact us message received',
            body_text=body_text,
            body_html = body_html
        )

    slack_message = f"""Contact form submitted from *{email}*\n *Message*: {body_text}\n  """
    send_slack_message(slack_url, slack_message)

    return None

@celery.task(queue='queue1')
def deliver_free_tokens_email(email,recipient,message, slack_url):
    """
    Send free tokens request e-mail.

    :param email: E-mail address of the user
    :type user_id: str
    :return: None
    """

    u = User.find_by_identity(email)
    u.requested_tokens = False
    u.save()

    body_html = None
    with open("monstagpt/blueprints/contact/templates/contact/mail/free_tokens_html.txt", "r") as f: 
        contents = f.read() 
        body_html = contents.replace('{{user_email}}', email)
        body_html = body_html.replace('{{user_message}}', message)

    body_text = None
    with open("monstagpt/blueprints/contact/templates/contact/mail/free_tokens_text.txt", "r") as f: 
        contents = f.read() 
        body_text = contents.replace('{{user_email}}', email)
        body_text = body_text.replace('{{user_message}}', message)

    if send_email:
        send_template_message(
            recipient = recipient,
            subject = 'Free token request received',
            body_text=body_text,
            body_html = body_html
        )

    slack_message = f"""Free tokens requested from *{email}*\n *Message*: {body_text}\n  """
    send_slack_message(slack_url, slack_message)

    return None
