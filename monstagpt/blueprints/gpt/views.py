import datetime
import pytz
import json
from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import current_app
from flask_login import current_user
from flask_login import login_required
from sqlalchemy import text
from sqlalchemy import or_
from lib.util_json import render_json
from lib.util_datetime import tzware_datetime
import uuid
from monstagpt.extensions import csrf
from monstagpt.extensions import db
from monstagpt.blueprints.gpt.forms import BulkDeleteForm

from monstagpt.blueprints.gpt.decorators import tokens_required
from monstagpt.blueprints.gpt.decorators import subscription_required
from monstagpt.blueprints.gpt.models.question import ask_question

from monstagpt.blueprints.gpt.forms import ConversationForm
from monstagpt.blueprints.gpt.forms import QuestionForm
from monstagpt.blueprints.gpt.forms import FeedbackForm
from monstagpt.blueprints.gpt.models.gpt import Gpt
from monstagpt.blueprints.gpt.models.conversation import Conversation
from monstagpt.blueprints.stripe_payments.models import ProductCatalog
from monstagpt.blueprints.oai_webhook.models import Oaistatus
from monstagpt.blueprints.gpt.models.runing_tasks import RunningTasks
from monstagpt.blueprints.gpt.models.suggested_questions import Suggested
 
gpt = Blueprint('gpt', __name__, template_folder='templates', url_prefix='/gpt')

@gpt.before_request
@login_required
def before_request():
    """ Protect all of the gpt endpoints. """
    pass

@gpt.route('/ask_questions', methods=['GET','POST'])
def ask_questions():
    conversation = request.args.get('conversation')
    if request.method == "GET":
        if not conversation:
            flash("Please enter a name for the conversation.", "error")
            return redirect(url_for("gpt.main"))
        
        # Check if the record exists
        record_exists = (
            Gpt.query
            .filter(Gpt.user_id == current_user.id)
            .filter(Gpt.conversation_uuid == conversation)
            .first()
        )
        existing_conversation = False
        if record_exists:
            # Handle the case where the record exists
            existing_conversation = True

        recent_questions = (
        Gpt.query
        .filter(Gpt.user_id == current_user.id)
        .filter(Gpt.conversation_uuid == conversation)
        .order_by(Gpt.created_on.desc())
        .limit(10)
        )
        
        return render_template('gpt/questions.html',conversation=conversation,existing_conversation=existing_conversation, recent_questions=recent_questions)

    if request.method == "POST":
            conversation = request.form.get('conversation')
            coins = current_user.coins
            uid = current_user.id
            print(f"********* CONVERSATION is {conversation} ********")
            print(f'**** user has {coins} coins before message ****')
            
            message = request.form['question']
            if message:
                if coins < 1:
                    return jsonify({'error':'You need some more tokens'})
                # This prevents circular imports.
                from monstagpt.blueprints.gpt.tasks import ask_gpt_question
                task = ask_gpt_question.delay(uid, message,conversation)  # Dispatch the task.
                # Return a 202 ACCEPTED response, indicating that the request is in progress.
                # Also provide the client with the task's ID, so they can check up on it.
                return jsonify({'task_id': task.id}), 202  

            return jsonify({'error':'no message provided'})  # If no message provided, return an error.

@gpt.route('/get_time_until_question')
def get_time_until_question():
    current_time = tzware_datetime().timestamp()
    last_question_time = current_user.last_gpt_question
    subscription_name = 'Free'
    if current_user.subscription:
        subscription_name = current_user.subscription.plan
    product_catalog = ProductCatalog()
    rate_limit = product_catalog.query.filter_by(tier=subscription_name).first().rate_limit_seconds


    elapsed_time = current_time - last_question_time
    remaining_time = int(max(0, rate_limit - elapsed_time))
    
    return jsonify({"remaining_time": remaining_time})



@gpt.route('/handle_questions', methods=['POST'])
def handle_questions():
    # Check to see if the user has a subscription. If it has expired, set the subscription coins to zero.
    if current_user.subscription:
        time_now = datetime.datetime.now(pytz.utc).timestamp()
        print(f'time_now {int(time_now)}')
        if current_user.subscription.subscription_ends < time_now:
            current_user.subscribed_coins = 0
            current_user.subscription.status = 'expired'
            current_user.subscription.plan = 'Free'
            db.session.commit()

    remaining_time = get_time_until_question()
    remaining_time = remaining_time.get_data(as_text=True)
    remaining_time = json.loads(remaining_time)
    
    print('remaining time')
    print(remaining_time)
    if int(remaining_time['remaining_time']) > 0:
        return jsonify({'error':f'you still need to wait {remaining_time} seconds'})


    slack_critical_webhook_url = current_app.config.get("SLACK_CRITICAL_WEBHOOK_URL")
    # Extract data from the request body
    data = request.json
    conversation_uuid = data.get('conversation')
    question = data.get('question')

    print('DATA!!!!')
    print(question,conversation_uuid)
    
    coins = current_user.coins
    uid = current_user.id
    print(f"********* CONVERSATION is {conversation_uuid} ********")
    print(f'**** user has {coins} coins before message ****')
    print('***UID****')
    print(uid)
    if question:
        if (coins < 1) and (current_user.role != 'vip'):
            return jsonify({'error':'You need some more tokens'})
        # This prevents circular imports.
        from monstagpt.blueprints.gpt.tasks import ask_gpt_question
        task = ask_gpt_question.delay(uid, question,conversation_uuid,slack_critical_webhook_url)  # Dispatch the task.
        # Return a 202 ACCEPTED response, indicating that the request is in progress.
        # Also provide the client with the task's ID, so they can check up on it.
        return jsonify({'task_id': task.id}), 202  

    return jsonify({'error':'no message provided'})  # If no message provided, return an error.

@gpt.route('/get_questions/<conversation_uuid>', methods=['GET'])
def get_questions(conversation_uuid):
    recent_questions = (
        Gpt.query
        .filter(Gpt.user_id == current_user.id)
        .filter(Gpt.conversation_uuid == conversation_uuid)
        .filter(or_(Gpt.user_deleted.is_(None), Gpt.user_deleted == False))
        .order_by(Gpt.created_on.desc())
    ).all()

    results = [{"question": q.question, "answer": q.answer, "date": q.created_on} for q in recent_questions]
    
    return jsonify(results)

@gpt.route('/main', methods=['GET','POST'])
def main():
    # Check to see if the user has visited the pricing page, if not then redirect them there.
    if not current_user.has_seen_pricing:
        return redirect(url_for("stripe_payments.test"))
    
    # Check to see if the user has a subscription. If it has expired, set the subscription coins to zero.
    if current_user.subscription:
        time_now = datetime.datetime.now(pytz.utc).timestamp()
        print(f'time_now {int(time_now)}')
        if current_user.subscription.subscription_ends < time_now:
            current_user.subscribed_coins = 0
            current_user.subscription.status = 'expired'
            current_user.subscription.plan = 'Free'
            db.session.commit()
    
        # Get rate limit for users plan.
        plan = current_user.subscription.plan
    else:
        # User has never subscribed, plan is free by default
        plan = 'Free'

    rate_limit = ProductCatalog.query.filter_by(tier=plan).first().rate_limit_seconds
    
    bulk_form = BulkDeleteForm()
    form = ConversationForm()
    feedback_form = FeedbackForm()
    assistant_type = 'gpt4'
    if current_user.free_coins:
        assistant_type = 'gpt3.5'
    # Fetch the conversations directly from the Conversation table
    conversations = (
        Conversation.query
        .filter_by(user_id=current_user.id)
        .filter(or_(Conversation.user_deleted.is_(None), Conversation.user_deleted == False))
        .filter(Conversation.assistant_type == assistant_type)
        .order_by(Conversation.updated_on.desc())
    ).all()

    print('many conversations')
    # If you want to pass a list of dictionaries to the template
    conversations_list = [{'name': c.conversation_name, 'uuid': c.conversation_uuid, 'updated_on': c.updated_on} for c in conversations]
    print(conversations_list)
    suggested_questions = Suggested.query.order_by(Suggested.order).all()
    suggested_questions_json = json.dumps([{'question': q.question} for q in suggested_questions])
    print(suggested_questions_json)

    # if feedback_form.validate_on_submit():
    #     question = request.form.get("question")
    #     answer = request.form.get("answer")
    #     thread = request.form.get("thread_id")
    #     message = request.form.get("message")
    #     print(question)
    #     print(answer)
    #     print(thread)
    #     print(message)

    # Check if there are any openapi status issues
    openai_issues = db.session.query(Oaistatus).first() is not None
    return render_template('gpt/main.html',conversations_list=conversations_list,form=form,bulk_form=bulk_form,feedback_form = feedback_form, suggested_questions=suggested_questions_json,openai_issues=openai_issues,rate_limit=rate_limit)

@gpt.route('/thumbsup', methods=['POST'])
def thumbsup():
    # Extract data from the request body
    data = request.json
    question = data.get("question")
    answer = data.get("answer")
    thread = data.get("thread")

    if 'thread_' in thread:
        # Your Slack message sending logic
        slack_feedback_webhook_url = current_app.config.get("SLACK_FEEDBACK_WEBHOOK_URL")
        print('*******FEEDBACK WEBHOOK URL******')
        print(slack_feedback_webhook_url)
        slack_message = f"""Positive feedback from *{current_user.email}*\n *Question*: {question}\n GPT response: {answer}\n *Thread ID*:{thread} """
        # avoiding circular imports
        from lib.custom_logging_handler import send_slack_message
        send_slack_message(slack_feedback_webhook_url, slack_message)
        print(slack_message)
        
    return jsonify({'message':'sent yo'})  

@gpt.route('/feedback', methods=['POST'])
def feedback():
    # Extract data from the request body
    data = request.json
    question = data.get("question")
    answer = data.get("answer")
    thread = data.get("thread")
    message = data.get("message")


    send_email = False

    if 'thread_' in thread:
        if send_email:
            recipient = current_app.config.get("MAIL_DEFAULT_TO")
            from monstagpt.blueprints.gpt.tasks import deliver_question_feedback_email
            deliver_question_feedback_email.delay(current_user.email,recipient, question,answer,thread,message)

        # Your Slack message sending logic
        slack_feedback_webhook_url = current_app.config.get("SLACK_FEEDBACK_WEBHOOK_URL")
        print('*******FEEDBACK WEBHOOK URL******')
        print(slack_feedback_webhook_url)
        slack_message = f"""Feedback form submitted from *{current_user.email}*\n *Question*: {question}\n GPT response: {answer}\n *User message*:{message}\n *Thread ID*:{thread} """
        # avoiding circular imports
        from lib.custom_logging_handler import send_slack_message
        send_slack_message(slack_feedback_webhook_url, slack_message)
        

    return jsonify({'message':'sent yo'})  

@gpt.route('/cancel_task', methods=['POST'])
def cancel_task():

    # Extract data from the request body
    data = request.json
    task_id = data.get("task_id")
    print('**** CANCELLING THE TASK')
    task_to_update = RunningTasks.query.filter_by(task_id=task_id).first()
    # If a task with the given ID exists, update its 'cancelled' status
    if task_to_update:
        task_to_update.cancelled = True
        db.session.commit()
    # # At some point later, deciding to revoke the task
    # # celery.control.revoke(task_id, terminate=True, signal='SIGTERM')
    # print(f'****** TASK ID ****** {task_id}')
    return jsonify({'message':'sent yo'})  

@gpt.post("/convo_bulk_delete")
def convo_bulk_delete():
    form = BulkDeleteForm()
    print('form scope:')
    print(request.form.getlist("bulk_ids"))
    if form.validate_on_submit():
        ids = Conversation.get_bulk_action_ids(
            request.form.get("scope"),
            request.form.getlist("bulk_ids"),
            omit_ids=[current_user.id],
            query=request.args.get("q", text("")),
        )
        
        Conversation.bulk_delete_uuid(ids)

        flash(
            "{0} conversation(s) were deleted.".format(len(ids)),
            "success",
        )
    else:
        flash("No conversations were deleted, something went wrong.", "error")

    return redirect(url_for("gpt.main"))


@gpt.route('/list_conversations')
def list_conversations():
    assistant_type = 'gpt4'
    if (current_user.free_coins) or (current_user.role == 'vip'):
        assistant_type = 'gpt3.5'
    # Fetch the conversations directly from the Conversation table
    conversations = (
        Conversation.query
        .filter_by(user_id=current_user.id)
        .filter(or_(Conversation.user_deleted.is_(None), Conversation.user_deleted == False))
        .filter(Conversation.assistant_type == assistant_type)
        .order_by(Conversation.updated_on.desc())
    ).all()
    conversations_list = [{'name': c.conversation_name, 'uuid': c.conversation_uuid, 'updated_on': c.updated_on} for c in conversations]
    # for conversation in conversations:
    #     conversation['updated_on'] = conversation['updated_on'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(conversations_list)

@gpt.route('/create_new_conversation', methods=['GET','POST'])
def create_new_conversation():
    data = request.json
    conversation_name = data['conversation_name']
    conversation_uuid = str(uuid.uuid4())
    params = {
        "conversation_name": conversation_name,
        "conversation_uuid": conversation_uuid,
        "user_id": current_user.id
    }

    conversation_db = Conversation(**params)
    conversation_db.save()

    return jsonify({
        'conversation_name': conversation_name,
        'conversation_uuid': conversation_uuid
    })

@gpt.route('/update-conversation-name/<uuid>', methods=['POST'])
def update_conversation_name(uuid):
    print('UUID***')
    print(uuid)
    try:
        # Get the new name from the request data
        data = request.json
        new_name = data.get('new_name')
        print('***new_name****')
        print(new_name)
        # Fetch the conversation using the provided UUID
        conversation = Conversation.query.filter_by(conversation_uuid=uuid).first()
        
        # Check if the conversation exists
        if not conversation:
            return jsonify(success=False, error="Conversation not found.")

        # Update the conversation's name and commit the changes
        conversation.conversation_name = new_name
        conversation.save()

        return jsonify(success=True)
        
    except Exception as e:
        return jsonify(success=False, error=str(e))
    
@gpt.route('/result/<task_id>')
def task_result(task_id):
    from monstagpt.blueprints.gpt.tasks import ask_gpt_question
    task = ask_gpt_question.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task not yet complete...'
        }
    elif task.state != 'FAILURE':
        response,coins,conversation_uuid = task.result
        response = {
            'state': task.state,
            'result': {'response': response, 'coins': coins, 'conversation_uuid':conversation_uuid}
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }
    return jsonify(response)

    
@gpt.get("/history", defaults={"page": 1})
@gpt.get("/history/page/<int:page>")
def history(page):
    paginated_questions = (
        Gpt.query.filter(Gpt.user_id == current_user.id)
        .order_by(Gpt.created_on.desc())
        .paginate(page=page, per_page=20)
    )

    return render_template("gpt/history.html", questions=paginated_questions)


@gpt.post("/gpt_webhook")
@csrf.exempt
def event():
    if not request.json:
        return render_json(406, {"error": "Mime-type is not application/json"})

    data = request.json

    recipient = 'mpwjames@gmail.com'
    question = 'question'
    answer = 'answer'
    thread = 'thread'
    message = data
    from monstagpt.blueprints.gpt.tasks import deliver_question_feedback_email
    deliver_question_feedback_email.delay('test@test.com',recipient, question,answer,thread,message)

    return render_json(200, {"success": True})