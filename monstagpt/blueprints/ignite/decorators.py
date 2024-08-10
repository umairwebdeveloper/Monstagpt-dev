from functools import wraps

from flask import flash
from flask import redirect
from flask import url_for
from flask import request
from flask import jsonify
from flask import current_app

def parameters_required(f):
    """
    restrict access to users who have a validated api key.

    return: Function
    """

    # @wraps(f)
    # def decorated_function(*args, **kwargs):
    #     stored_api_key = current_app.config.get("IGNITE_API_KEY")
    #     apikey = request.args.get('apikey',None)

    #     if not apikey:
    #         return jsonify({'message' : 'apikey is missing'}, 401)
        
    #     # check if the provided api_key matches the stored one
    #     if apikey != stored_api_key:
    #         return jsonify({'message' : 'API key is invalid'}, 401)
        
    #     # id = request.args.get('id',None)
    #     # platform = request.args.get('platform',None)
    #     # start_date = request.args.get('start_date',None)
    #     # end_date = request.args.get('end_date')
    #     # payload = {'id':id,'platform':platform,'start_date':start_date,'end_date':end_date}
    #     # # read the message
    #     # payload = request.get_json()
    #     # if not payload:
    #     #     return jsonify({'message': 'Missing parameters'}, 400)
        
    #     # return f(payload, *args, **kwargs)
    #     return f(*args, **kwargs)
    # return decorated_function

    @wraps(f)
    def decorated_function(*args, **kwargs):
        stored_api_key = current_app.config.get("IGNITE_API_KEY")

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not 'x-access-token' in request.headers:
            return jsonify({'message' : 'x-access-token is missing from header'}, 401)
        
        if not token:
            return jsonify({'message' : 'API key is missing'}, 401)
   
        if token != stored_api_key:
            return jsonify({'message' : 'API key is invalid'}, 401)
        
        
        # id = request.args.get('id',None)
        # platform = request.args.get('platform',None)
        # start_date = request.args.get('start_date',None)
        # end_date = request.args.get('end_date')
        # payload = {'id':id,'platform':platform,'start_date':start_date,'end_date':end_date}
        # # read the message
        # payload = request.get_json()
        # if not payload:
        #     return jsonify({'message': 'Missing parameters'}, 400)
        
        # return f(payload, *args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function
