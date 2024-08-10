from functools import wraps

from flask import flash
from flask import redirect
from flask import url_for
from flask import request
from flask_login import current_user
from flask import jsonify
from monstagpt.blueprints.api.models import Api

def api_key_required(f):
    """
    restrict access to users who have a validated api key.

    return: Function
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not 'x-access-token' in request.headers:
            return jsonify({'message' : 'x-access-token is missing from header'}, 401)
        
        if not token:
            return jsonify({'message' : 'API key is missing'}, 401)
        
        # check if the api key exists in the database
        api_db = Api()
        user = api_db.find_user_by_api_key(token)
        if user is None:
            return jsonify({'message' : 'API key is invalid'}, 401)
        
        # read the message
        message = request.get_json()

        # if not message.get('question'):
        #     return jsonify({'message' : 'Please make sure a question is in the payload'}, 406)
        
        # if message['question'] == '':
        #     return jsonify({'message' : 'Please ask a question'}, 406)
        
        return f(user, message, *args, **kwargs)
    
    return decorated_function
