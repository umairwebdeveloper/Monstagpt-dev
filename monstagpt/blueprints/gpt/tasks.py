from flask import jsonify
from flask_login import current_user
from monstagpt.app import create_celery_app
from lib.flask_mailplus import send_template_message
from lib.custom_logging_handler import send_slack_message
from monstagpt.blueprints.gpt.models.gpt import Gpt
from monstagpt.blueprints.gpt.models.question import ask_question
from monstagpt.blueprints.user.models import User
from monstagpt.blueprints.gpt.models.runing_tasks import RunningTasks
from monstagpt.blueprints.gpt.models.conversation import Conversation
from monstagpt.extensions import db
import uuid

celery = create_celery_app()

def check_cancelled(task_id):
    # Re-query the RunningTasks object to ensure you have the latest state
    running_task = db.session.query(RunningTasks).filter_by(task_id=task_id).first()
    db.session.refresh(running_task)
    print(running_task)
    return running_task.cancelled

@celery.task(bind=True,queue='queue2')
def ask_gpt_question(self, uid,message,conversation_uuid,slack_critical_webhook_url):
    print('*****IN GPT QUESTION****')
    task_id = self.request.id

    params = {
        "task_id": task_id,
        }

    running_task = RunningTasks(**params)
    running_task.save()

    print(f"Task ID: {task_id}")
    print("****UID*****")
    print(uid)
    user = User.query.get(uid)

    if user is None:
        return
    
    free_mode = False
    assistant_type = 'gpt4'
    free_coins = user.free_coins
    # if user.role == 'vip' or free_coins <= 0:
    if free_coins > 0 or user.role == 'vip':
        free_mode = True
        assistant_type = 'gpt3.5'

    new_conversation = False
    if not conversation_uuid:
        new_conversation = True
        # no conversation selected, generate a new one
        # conversation_uuid = uuid.uuid4().hex
    
    print('*****CONVERSATION_UUID****')
    print(conversation_uuid)
    print(user.id)

    if check_cancelled(task_id):
        return 'question cancelled by user',user.coins, conversation_uuid
    response,prompt_tokens,completion_tokens,total_cost,thread_id,queries_and_response = ask_question(message,conversation_uuid,user,free_mode,task_id)
                # #response =  agent.run(message)
                # extra_command = 'For downloads question use the table_downloads table. For revenue question use the table_revenue table. Run the query and give me the results'
                # response = agent_executor.run(f'{message}. {extra_command}')

    if check_cancelled(task_id):
        return 'question cancelled by user',user.coins,thread_id
    
    print("****queries_and_response*****")
    print(queries_and_response)
    print('***response****')
    print(response)

    if not response:
        response = 'An error occurred while processing your request.'

    if new_conversation:
        a = response.split(' ')
        convo_name = ''

        if len(a) < 6:
            convo_name = response
        else:
            for i in range(6):
                convo_name += a[i] + ' '
            convo_name += '...'  
        params = {
        # first 6 words of the response can be the saved name
        "conversation_name": convo_name,
        "conversation_uuid": thread_id,
        "user_id": user.id,
        "assistant_type": assistant_type
        }

        conversation_db = Conversation(**params)
        conversation_db.save()

    if check_cancelled(task_id):
        return 'question cancelled by user',user.coins, thread_id
    
    # the sql query and response needs to be limited to 5000 chars
    if len(str(queries_and_response)) >= 5000:
        queries_and_response = str(queries_and_response)[0:5000]

    params = {
        "user_id": user.id,
        "conversation_uuid": thread_id,
        "question": message,
        "answer": str(response),
        "sql": str(queries_and_response),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_cost": total_cost
    }

    gpt_db = Gpt(**params)
    if response == 'An error occurred while processing your request.':
        gpt_db.save_and_update_user(user,error=True)
        # Your Slack message sending logic
        slack_message = f"""User *{user.email}* just experienced an error with a question\n *Question*: {message}\n *GPT response*: {str(response)}\n *Thread ID*:{thread_id} """
        send_slack_message(slack_critical_webhook_url, slack_message)
    else:
        gpt_db.save_and_update_user(user)
    coins = user.coins

    # Delete the task from the running_tasks table
    task_to_delete = RunningTasks.query.filter_by(task_id=task_id).first()
    task_to_delete.delete()
    print(f'**** user has {coins} coins left ****')
    return str(response),user.coins, thread_id


@celery.task(queue='queue1')
def deliver_question_feedback_email(email,recipient, question,answer,thread,message):
    """
    Send a gpt question feedback e-mail.

    :param email: E-mail address of the visitor
    :type user_id: str
    :param message: E-mail message
    :type user_id: str
    :return: None
    """

    body_html = None
    with open("monstagpt/blueprints/gpt/templates/gpt/mail/index_html.txt", "r") as f: 
        contents = f.read() 
        body_html = contents.replace('{{user_email}}', email)
        body_html = body_html.replace('{{custom_question}}', question)
        body_html = body_html.replace('{{custom_answer}}', answer)
        body_html = body_html.replace('{{custom_message}}', message)
        body_html = body_html.replace('{{custom_thread}}', thread)


    body_text = None
    with open("monstagpt/blueprints/gpt/templates/gpt/mail/index_text.txt", "r") as f: 
        contents = f.read() 
        body_text = contents.replace('{{user_email}}', email)
        body_text = body_text.replace('{{custom_question}}', question)
        body_text = body_text.replace('{{custom_answer}}', answer)
        body_text = body_text.replace('{{custom_message}}', message)
        body_text = body_text.replace('{{custom_thread}}', thread)

    ctx = {"user_email": email, "message": message}

    # recipient=None,subject=None,body_text=None,body_html=None)
    send_template_message(
        recipient = recipient,
        subject = 'feedback received on a gpt question',
        body_text=body_text,
        body_html = body_html
    )

    return None