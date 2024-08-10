import logging
import requests
from flask import current_app
from lib.flask_mailplus import send_template_message

def send_slack_message(webhook_url, message):
    headers = {'Content-Type': 'application/json'}
    data = {"text": message}
    response = requests.post(webhook_url, json=data, headers=headers)
    if response.status_code != 200:
        raise ValueError(f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}")

class CustomLoggingHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        
        # Decide to send email, Slack notification, or both based on configuration or log level
        send_email = False  
        send_slack = True 

        if send_email:
            # Map log levels to subject prefixes
            subject_prefixes = {
                logging.DEBUG: "[Debug]",
                logging.INFO: "[Info]",
                logging.WARNING: "[Warning]",
                logging.ERROR: "[Error]",
                logging.CRITICAL: "[Critical]",
            }
            
            # Default subject prefix if level is not in the map (should not happen in practice)
            subject_prefix = subject_prefixes.get(record.levelno, "[Log]")
            
            subject = f"{subject_prefix} A log message was recorded"
            body_text = f"Time: {record.asctime}\nMessage type: {record.levelname}\n\nMessage:\n\n{record.message}"
            body_html = f"""<html>
            <head></head>
            <body>
            <h1>Time: {record.asctime}</h1>
            <h2>Message type: {record.levelname}</h2>
            <p>{log_entry}</p>
            </body>
            </html>"""
            
            send_template_message(
                recipient = current_app.config.get("MAIL_DEFAULT_TO"),
                subject=subject,
                body_text=body_text,
                body_html=body_html
            )

        if send_slack:
            # Your Slack message sending logic
            slack_critical_webhook_url = current_app.config.get("SLACK_CRITICAL_WEBHOOK_URL")
            print(f'url: {slack_critical_webhook_url}')
            slack_message = f"A log message was recorded:\n{log_entry}"
            send_slack_message(slack_critical_webhook_url, slack_message)