from lib.flask_mailplus import send_template_message
from monstagpt.app import create_celery_app
from monstagpt.blueprints.user.models import User
import os
# from flask import url_for
celery = create_celery_app()


@celery.task(queue='queue1')
def deliver_password_reset_email(user_id, reset_token):
    """
    Send a reset password e-mail to a user.

    :param user_id: The user id
    :type user_id: int
    :param reset_token: The reset token
    :type reset_token: str
    :return: None if a user was not found
    """
    user = User.query.get(user_id)

    if user is None:
        return
    BASE_URL = os.getenv("BASE_URL",'https://beta.appmonsta.ai')
    # url = url_for('user.password_reset', reset_token=reset_token, _external=True)
    url = f'{BASE_URL}/account/password_reset?reset_token={reset_token}'
    body_html = None
    with open("monstagpt/blueprints/user/templates/user/mail/password_reset_html.txt", "r") as f: 
        contents = f.read() 
        body_html = contents.replace('{{ reset_token }}', url)
        body_html = body_html.replace('{{ email }}', user.email)

    body_text = None
    with open("monstagpt/blueprints/user/templates/user/mail/password_reset_html.txt", "r") as f: 
        contents = f.read() 
        body_text = contents.replace('{{ reset_token }}', url)
        body_text = body_text.replace('{{ email }}', user.email)

    ctx = {"user": user, "reset_token": reset_token}
    # recipient=None,subject=None,body_text=None,body_html=None
    send_template_message(
        recipient = user.email,
        subject="Password reset from MonstaGPT",
        body_text=body_text,
        body_html=body_html
    )

    return None

@celery.task(queue='queue1')
def deliver_confirmation_email(user_id, confirmation_token):
    """
    Send a confirmation e-mail to a user.

    :param user_id: The user id
    :type user_id: int
    :param reset_token: The confirmation token
    :type reset_token: str
    :return: None if a user was not found
    """
    user = User.query.get(user_id)
    print('**Sending email to**')
    print(user.email)
    if user is None:
        return

    BASE_URL = os.getenv("BASE_URL",'https://beta.appmonsta.ai')
    email_address = user.email
    # email_address = 'matthew.james@appmonsta.com'
    # url = url_for('user.confirm_email', confirmation_token=confirmation_token, _external=True)
    url = f'{BASE_URL}/account/confirm_email?confirmation_token={confirmation_token}'
    body_html = None
    with open("monstagpt/blueprints/user/templates/user/mail/confirmation_email_html.txt") as f:
        contents = f.read()
        body_html = contents.replace('{{ email }}', user.email)
        body_html = body_html.replace('{{ confirmation_token }}', url)


    body_text = None
    with open("monstagpt/blueprints/user/templates/user/mail/confirmation_email_text.txt") as f:
        contents = f.read()
        body_text = contents.replace('{{ email }}', user.email)
        body_text = body_text.replace('{{ confirmation_token }}',url)

    print(body_html)
    print('text')
    print(body_text)

    send_template_message(
        recipient = email_address,
        subject='Welcome to MonstaGPT',
        body_text = body_text,
        body_html = body_html
        )

    return None