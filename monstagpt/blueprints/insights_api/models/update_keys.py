import os
import requests
from monstagpt.blueprints.user.models import User

auth_key = os.getenv('INSIGHTS_API_KEY',None)
slack_critical_webhook_url = os.getenv('SLACK_CRITICAL_WEBHOOK_URL')


def update_subscription_keys(email,tier,start_date,end_date):
    from lib.custom_logging_handler import send_slack_message
    print(auth_key)
    url = 'http://54.173.26.106:5000/gpt-subscription/new-subscription'
    headers = {
        'Authorization': auth_key,
        'Content-Type': 'application/json'
    }
    data = {
    "email": email,
    "tier": tier,
    "start_date": start_date,
    "end_date": end_date
    }

    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)
    if response.status_code == 200:
        data = response.json()
        api_key_list = data['response']['api_keys']
        u = User.find_by_identity(email)
        if not u:
            slack_message = f"""Cannot get insights api keys for *{email}* as the user not present in db."""
            send_slack_message(slack_critical_webhook_url, slack_message)
            return None
        print(response.json())
        # Convert the list into a single string with each item on a new line
        api_keys_string = "\n".join(api_key_list)
        u.insights_keys = api_keys_string
        u.save()

        return api_keys_string
    print('error with the endpoint')
    slack_message = f"""Failed to fetch insights api keys for *{email}*. Check that they have them and that they are still active"""
    send_slack_message(slack_critical_webhook_url, slack_message)

    return None

def fetch_api_key_usage(key,start_date,end_date,status_code):
    from lib.custom_logging_handler import send_slack_message
    url = 'http://54.173.26.106:5000/dashboard-api/api-key-usage'
    headers = {
        'Authorization': auth_key,
        'Content-Type': 'application/json'
    }
    data = {
        "api_key": key,
        "start_date": start_date,
        "end_date": end_date,
        "status_code": status_code
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
            slack_message = f"""error retrieving insights api history for {key}"""
            send_slack_message(slack_critical_webhook_url, slack_message)
    response = requests.post(url, headers=headers, json=data)
    return response