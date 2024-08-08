from datetime import datetime
import json
from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from flask_babel import gettext as _
from monstagpt.blueprints.ignite.decorators import parameters_required
from monstagpt.extensions import db


import uuid

ignite = Blueprint('ignite', __name__, template_folder='templates',url_prefix='/ignite')


from sqlalchemy import create_engine, Column, String, select, Float, Date, text, or_
from sqlalchemy.orm import declarative_base, sessionmaker

# Define the base class for ORM
Base = declarative_base()

# Define your database connection string
DATABASE_URL = 'postgresql://readonly_user:4d82@postgres.csl.us-east-1.rds.amazonaws.com:5432/data'


# Create the database engine
engine = create_engine(DATABASE_URL)

# Define sessionmaker
Session = sessionmaker(bind=engine)

# @ignite.before_request
# def before_request():
#     """Protect all of the admin endpoints."""
#     if request.method == "OPTIONS":
#         res = Response()
#         res.headers['X-Content-Type-Options'] = '*'
#         return res
#     pass

@ignite.route('/reviews')
@parameters_required
def reviews():
    from monstagpt.blueprints.ignite.tasks import get_reviews_data
    app_id = request.args.get('id',None)
    platform = request.args.get('platform',None)
    start_date = request.args.get('start_date',None)
    end_date = request.args.get('end_date',None)
    if not app_id or not platform or not start_date or not end_date:
        return jsonify({'message' : 'Please include all of id, platform, start_date, end_date'}, 406)
    task = get_reviews_data.delay(app_id, platform, start_date, end_date)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  


@ignite.route('/rankings')
@parameters_required
def rankings():
    from monstagpt.blueprints.ignite.tasks import get_rankings_data
    app_id = request.args.get('id',None)
    platform = request.args.get('platform',None)
    start_date = request.args.get('start_date',None)
    end_date = request.args.get('end_date',None)
    if not app_id or not platform or not start_date or not end_date:
        return jsonify({'message' : 'Please include all of id, platform, start_date, end_date'}, 406)
    task = get_rankings_data.delay(app_id, platform, start_date, end_date)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  

@ignite.route('/downloads')
@parameters_required
def downloads():
    from monstagpt.blueprints.ignite.tasks import get_downloads_data
    app_id = request.args.get('id',None)
    platform = request.args.get('platform',None)
    start_date = request.args.get('start_date',None)
    end_date = request.args.get('end_date',None)
    if not app_id or not platform or not start_date or not end_date:
        return jsonify({'message' : 'Please include all of id, platform, start_date, end_date'}, 406)
    task = get_downloads_data.delay(app_id, platform, start_date, end_date)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  

@ignite.route('/details')
@parameters_required
def details():
    from monstagpt.blueprints.ignite.tasks import get_details_data
    app_id = request.args.get('id',None)
    platform = request.args.get('platform',None)
    if not app_id or not platform:
        return jsonify({'message' : 'Please include an id and platform'}, 406)
    task = get_details_data.delay(app_id, platform)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  

@ignite.route('/data_safety',methods=['GET','POST'])
@parameters_required
def data_safery():
    print(f'******* HERE')
    from monstagpt.blueprints.ignite.tasks import get_data_safety_data
    app_id = request.args.get('id',None)
    platform = request.args.get('platform',None)
    start_date = request.args.get('start_date',None)
    end_date = request.args.get('end_date')
    print(f'******* PLATFORM {platform}')
    if not app_id or not platform:
        return jsonify({'message' : 'Please include an id and platform'}, 406)
    task = get_data_safety_data.delay(app_id, platform)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  

@ignite.route('/revenue',methods=['GET','POST'])
@parameters_required
def revenue():
    from monstagpt.blueprints.ignite.tasks import get_revenue_data as grd
    app_id = request.args.get('id',None)
    platform = request.args.get('platform',None)
    start_date = request.args.get('start_date',None)
    end_date = request.args.get('end_date',None)
    if not app_id or not platform or not start_date or not end_date:
        return jsonify({'message' : 'Please include all of id, platform, start_date, end_date'}, 406)
    task = grd.delay(app_id, platform, start_date, end_date)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  

@ignite.route('/top_estimates')
@parameters_required
def top_estimates():
    from monstagpt.blueprints.ignite.tasks import get_top_estimates
    data_type = request.args.get('data_type',None)
    platform = request.args.get('platform',None)
    start_date = request.args.get('start_date',None)
    end_date = request.args.get('end_date',None)
    limit = request.args.get('limit',None)
    if not data_type or not platform or not start_date or not end_date:
        return jsonify({'message' : 'Please include all of id, platform, start_date, end_date'}, 406)
    task = get_top_estimates.delay(data_type, platform, start_date, end_date, limit)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
    return jsonify({'task_id': task.id}), 202  


@ignite.route('/app_names')
@parameters_required
def app_names():
    from monstagpt.blueprints.ignite.tasks import get_name_by_id_and_platform
    from monstagpt.blueprints.ignite.tasks import get_id_by_name_and_platform
    app_id = request.args.get('id',None)
    app_platform = request.args.get('platform',None)
    app_name = request.args.get('name',None)
    if not request.args.get('platform'):
        return jsonify({'message' : 'Please select the platform - itunes or android'}, 406)
    if app_id:
        task = get_name_by_id_and_platform.delay(app_id, app_platform)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
        return jsonify({'task_id': task.id}), 202  
    if app_name:
        task = get_id_by_name_and_platform.delay(app_name, app_platform)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
        return jsonify({'task_id': task.id}), 202  
    return jsonify({'message' : 'Please return an app id or app name'}, 406)

@ignite.route('/task-status/<task_id>')
@parameters_required
def task_status(task_id):
    from monstagpt.app import create_celery_app
    celery = create_celery_app()
    task = celery.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'result': task.result  # Directly access the task result
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'status': 'Failed',
            'error': str(task.info),  # Detailed error information
        }
    else:
        response = {
            'state': task.state,
            'status': 'Processing...'
        }

    return jsonify(response)



# # Example usage
# app_id = "some_id"
# app_platform = "some_platform"
# app_name = get_name_by_id_and_platform(app_id, app_platform)
    


    # uid = user.id
    # coins = user.coins
    # if coins < 1:
    #     return jsonify({'error':'You need some more tokens'})
    #  # This prevents circular imports.
    # from monstagpt.blueprints.gpt.tasks import ask_gpt_question
    # task = ask_gpt_question.delay(uid, message["question"], message["conversation_id"])  # Dispatch the task.
 
    # return jsonify({'task_id': task.id}), 202  