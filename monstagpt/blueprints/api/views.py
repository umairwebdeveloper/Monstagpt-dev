from datetime import datetime
from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_login import current_user
from flask_login import login_required
from flask_babel import gettext as _
from sqlalchemy import or_

import uuid

from monstagpt.blueprints.gpt.decorators import subscription_required
from monstagpt.blueprints.api.decorators import api_key_required
from monstagpt.blueprints.api.models import Api
from monstagpt.blueprints.gpt.models.conversation import Conversation
from monstagpt.blueprints.gpt.models.gpt import Gpt
from monstagpt.blueprints.api.forms import DeleteKeyForm

api = Blueprint('api', __name__, template_folder='templates',url_prefix='/api')

@api.before_request
def before_request():
    """ Protect all of the api endpoints. """
    pass

@api.route("/add", methods=["GET"])
@login_required
def add_key():
    if len(current_user.api) >=4:
        flash('you have reached the maximum number of keys','error')
        return redirect(url_for("user.settings"))
    public_id=uuid.uuid4().hex
    params = {
        "user_id": current_user.id,
        "api_key": public_id,
    }
    api_db = Api(**params)
    api_db.save_and_update_user(current_user)

    return redirect(url_for("user.settings"))

@api.route("/remove_key", methods = ["POST"])
@login_required
def remove_key():
    if not current_user.api:
        flash(_("You do not have any api keys."), "error")
        return redirect(url_for("user.settings"))
    
    form = DeleteKeyForm()

    if form.validate_on_submit():
        api_key = form.api_key.data
        # Now you can use `api_key` to delete the key
        # Add your key deletion code here
        # ...
        print(api_key)
        api_db = Api()
        delete_result = api_db.delete_and_update_user(current_user, api_key)
        
        return redirect(url_for('user.settings'))  # Redirect to the page with the forms
    else:
        # Handle form validation errors here
        # ...
        flash('some error occured',"error")
        return redirect(url_for('user.settings'))  # Redirect to the page with the forms
    
@api.route("/get_conversations")
@api_key_required
def get_conversations(user,message):
    if not user.subscription:
        return jsonify({'message' : 'You need an active subscription'}, 403)
    conversations = (
    Conversation.query
        .filter_by(user_id=user.id)
        .filter(or_(Conversation.user_deleted.is_(None), Conversation.user_deleted == False))
        .order_by(Conversation.updated_on.desc())
    ).all()

    print('many conversations')
    # If you want to pass a list of dictionaries to the template
    conversations_list = [{'name': c.conversation_name, 'conversation_id': c.conversation_uuid, 'updated_on': c.updated_on} for c in conversations]

    return jsonify(conversations_list), 202  

@api.route("/get_questions")
@api_key_required
def get_questions(user,message):
    if not user.subscription:
        return jsonify({'message' : 'You need an active subscription'}, 403)
    conversation_uuid = message["conversation_id"]
    recent_questions = (
    Gpt.query
        .filter(Gpt.user_id == user.id)
        .filter(Gpt.conversation_uuid == conversation_uuid)
        .filter(or_(Gpt.user_deleted.is_(None), Gpt.user_deleted == False))
        .order_by(Gpt.created_on.desc())
    ).all()

    results = [{"question": q.question, "answer": q.answer} for q in recent_questions]

    return jsonify(results), 202


@api.route('/query')
@api_key_required
def test(user,message):
    if not user.subscription:
        return jsonify({'message' : 'You need an active subscription'}, 403)
    
    if not message.get('question'):
        return jsonify({'message' : 'Please make sure a question is in the payload'}, 406)
    
    if message['question'] == '':
        return jsonify({'message' : 'Please ask a question'}, 406)

    uid = user.id
    coins = user.coins
    if coins < 1:
        return jsonify({'error':'You need some more tokens'})
     # This prevents circular imports.
    from monstagpt.blueprints.gpt.tasks import ask_gpt_question
    task = ask_gpt_question.delay(uid, message["question"], message["conversation_id"])  # Dispatch the task.
 
    return jsonify({'task_id': task.id}), 202  

@api.route('/result/<task_id>')
def task_result(task_id):
    from monstagpt.blueprints.gpt.tasks import ask_gpt_question
    task = ask_gpt_question.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task not yet complete...'
        }
    elif task.state != 'FAILURE':
        response,coins, conversation_uuid = task.result
        response = {
            'state': task.state,
            'result': {'response': response, 'tokens left': coins, 'conversation_id':conversation_uuid},
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }
    print(jsonify(response))
    return jsonify(response)

@api.route('/remaining_tokens')
@api_key_required
def remaining_tokens(user,message):
    coins = user.coins
    results = {"bught_tokens": user.bought_coins, "subscription_tokens": user.subscribed_coins}

    return jsonify(results), 202
    
@api.route('/docs')
def docs():

    return render_template("index.html")

@api.route('/appmonsta_docs')
def appmonsta_docs():

    return render_template("appmonsta_api.html")