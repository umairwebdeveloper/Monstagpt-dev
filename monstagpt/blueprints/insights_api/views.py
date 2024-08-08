import pandas as pd
from collections import defaultdict
from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import url_for
from flask_login import current_user
from flask_login import login_required
from monstagpt.blueprints.insights_api.models.update_keys import update_subscription_keys
from monstagpt.blueprints.insights_api.models.update_keys import fetch_api_key_usage

insights_api = Blueprint('insights_api', __name__, template_folder='templates',url_prefix='/insights')

@insights_api.before_request
@login_required
def before_request():
    """ Protect all of the api endpoints. """
    pass

@insights_api.route('/update_keys')
def update_keys():
    keys = update_subscription_keys(current_user.email,'standard','2024-07-31','2024-08-31')
    print(keys)
    return 'sup, to'

@insights_api.route('/display_key_usage')
def display_key_usage():
    user_keys = current_user.insights_keys
    # Get the current users insights keys
    keys_list = current_user.insights_keys.split('\n')
    # Strip any unwanted characters from key_list
    cleaned_keys = [key.strip() for key in keys_list]
    result = {}
    for key in cleaned_keys:
        response_data = fetch_api_key_usage(key,'2024-06-31','2024-07-31','0')
        if response_data.status_code == 200:
            # Initialize the list for this API key
            result[key] = []
            # Iterate over the output and build the list of dictionaries
            for date, count in response_data['output'].items():
                result[key].append({'date': date, 'count': count})
        else:
            print(f"Failed to fetch data for API key: {key}")
    return result

@insights_api.route('/')
def index():
    if (not current_user.subscription) or (current_user.subscription.status == 'expired') or (current_user.role != 'admin'):
        return redirect(url_for("stripe_payments.test",referer='insights_api'))
    elif current_user.insights_keys:
        results = {}
        for api_key in current_user.insights_keys.split('\n'):
            print(f"key: {api_key}")

            response = fetch_api_key_usage(api_key,'2024-07-29','2024-07-31','0')
            
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                response_data = response.json()
                
                # Initialize the list for this API key
                results[api_key] = []
                
                # Iterate over the output and build the list of dictionaries
                for date, count in response_data['output'].items():
                    results[api_key].append({'date': date, 'count': count})
            else:
                print(f"Failed to fetch data for API key: {api_key}")
        print(results)
        return render_template(
            "insights_api/index.html", api_data = results)

    else:
        return render_template(
            "insights_api/index.html", api_data = {})