from flask import render_template
from monstagpt.extensions import mail
from flask import current_app



import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_template_message(recipient=None,subject=None,body_text=None,body_html=None,**kwargs):
    if kwargs:
        print(f"Unexpected arguments passed: {kwargs}")
    # replace sender@example.com with your From address.
    # This address must be verified
    SENDER = current_app.config.get("MAIL_DEFAULT_SENDER")

    SENDERNAME = 'App Monsta'

    # replace recipient@example.com with a To address. If you account
    # is still in the sandbox, this address must be verified.
    RECIPIENT = recipient

    # replace smtp_username with youe Amazon SES SMTP user name.
    USERNAME_SMTP = current_app.config.get("MAIL_USERNAME")

    # replace smtp_password with youe Amazon SES SMTP password.
    PASSWORD_SMTP = current_app.config.get("MAIL_PASSWORD")

    # (Optional) the name of a configuration set to use for this message.
    # if you comment out this line, you also need to remove or comment out
    # the "X-SES-CONFIGURATION-SET:" heaser below.

    CONFIGURATION_SET = 'ConfigSet'

    # if you're using Amazon SES in the AWS Region other than US West (Oregon),
    # replace 'email-smtp.us-west2.amazonaws.com with the Amazon SES SMTP
    # endpoint in the appropriate region.
    HOST = current_app.config.get("MAIL_SERVER")
    PORT = current_app.config.get("MAIL_PORT")

    # The subject line of the email.
    SUBJECT = subject

    BODY_TEXT = body_text
    BODY_HTML = body_html

    # create message container - the correct MIME type is multipart/alternative/
    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['FROM'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = RECIPIENT
    # comment or delete the next line if you are not using a configuration set

    # msg.add_header('X-SES-CONFIGURATION-SET', CONFIGURATION_SET)

    # record the MIME types od both parts - text/plain and text/html
    part1 = MIMEText(BODY_TEXT, 'plain')
    part2 = MIMEText(BODY_HTML, 'html')

    # attach parts into message container
    # according to RFC 2046, the last part of a multipart message, in this case
    # tbe HTML message, is the best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    # try to send the message
    try:
        server = smtplib.SMTP(HOST, PORT)
        server.ehlo()
        server.starttls()
        # smtplib docs recommwnr calling ehlo() before & after starttls()
        server.ehlo()
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        server.sendmail(SENDER,RECIPIENT, msg.as_string())
        server.close()
    # display an error message if something went wrong
    except Exception as e:
        print('error: ',e)
    else:
        print('email sent')

    return None

def send_template_message_old(template=None, ctx=None, *args, **kwargs):
    """
    Send a templated e-mail using a similar signature as Flask-Mail:
    http://pythonhosted.org/Flask-Mail/

    Except, it also supports template rendering. If you want to use a template
    then just omit the body and html kwargs to Flask-Mail and instead supply
    a path to a template. It will auto-lookup and render text/html messages.

    Example:
        ctx = {'user': current_user, 'reset_token': token}
        send_template_message('Password reset from Foo', ['you@example.com'],
                              template='user/mail/password_reset', ctx=ctx)

    :param subject:
    :param recipients:
    :param body:
    :param html:
    :param sender:
    :param cc:
    :param bcc:
    :param attachments:
    :param reply_to:
    :param date:
    :param charset:
    :param extra_headers:
    :param mail_options:
    :param rcpt_options:
    :param template: Path to a template without the extension
    :param context: Dictionary of anything you want in the template context
    :return: None
    """
    if ctx is None:
        ctx = {}

    if template is not None:
        if "body" in kwargs:
            raise Exception("You cannot have both a template and body arg.")
        elif "html" in kwargs:
            raise Exception("You cannot have both a template and body arg.")

        kwargs["body"] = _try_renderer_template(template, **ctx)
        kwargs["html"] = _try_renderer_template(template, ext="html", **ctx)

    mail.send_message(*args, **kwargs)

    return None


def _try_renderer_template(template_path, ext="txt", **kwargs):
    """
    Attempt to render a template. We use a try/catch here to avoid having to
    do a path exists based on a relative path to the template.

    :param template_path: Template path
    :type template_path: str
    :param ext: File extension
    :type ext: str
    :return: str
    """
    try:
        return render_template("{0}.{1}".format(template_path, ext), **kwargs)
    except IOError:
        pass
