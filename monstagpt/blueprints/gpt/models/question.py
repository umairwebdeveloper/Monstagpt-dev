import json
import os
import re
import time
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from lib.custom_logging_handler import send_slack_message
from monstagpt.blueprints.gpt.models.runing_tasks import RunningTasks
from monstagpt.extensions import db

slack_critical_webhook_url = 'https://hooks.slack.com/services/T'

DATABASE_URI = 'postgresql://postgres:fHc@ges.csl.us-east-1.rds.amazonaws.com:5432/data'
# Create an engine
engine = create_engine(DATABASE_URI)
# Create a configured "Session" class
Session = sessionmaker(bind=engine)
client = OpenAI()

# Define the function to process messages
def process_messages(message):
    message_content = message.content[0].text.value
    message_content = re.sub(r'(\-\s[^\n]+)', r'<li>\1</li>', message_content)
    message_content = re.sub(r'(On [^\n]+)', r'<p>\1</p>', message_content)
    message_content = re.sub(r'(Would you like [^\n]+)', r'<p>\1</p>', message_content)
    message_content = re.sub(r'(<li>[\s\S]*<\/li>)', r'<ul>\1</ul>', message_content)
    return message_content

def query_details(query, queries_and_response, user, thread_id,question) -> str:
    print(query)
    return run_query(query, queries_and_response,user, thread_id,question)

def dictfetchall(cursor, fet_rows):
    """Returns all rows from a cursor as a list of dicts"""
    desc = cursor.description
    return [dict(zip([col[0] for col in desc], row))
            for row in fet_rows]

def run_query(query, queries_and_response, user, thread_id,question) -> str:
    session = Session()
    try:
        # Execute the SELECT query
        result_proxy = session.execute(text(query))
        results = result_proxy.fetchall()

        # Get column names
        column_names = result_proxy.keys()

        # Prepare the data as a list of lists
        table_data = [list(row) for row in results]

        # Convert data into JSON
        print("**** RESULTS ****")
        print(results)
        json_results: str = json.dumps(results, default=str)

        print('***JSON RESULTS****')
        print(json_results)
        return json_results

    except sqlalchemy.exc.SQLAlchemyError as e:
        # Specific SQLAlchemy exceptions can be caught here
        error_message = f"Error executing SQL query: {e}"
        print(error_message)
        queries_and_response.append({'query': query, 'output': error_message})
        return json.dumps({'error': error_message})

    except Exception as e:
        queries_and_response.append({'query': query, 'output': f"Error: {e}"})
        print(f"Error executing query: {e}")
        json_results: str = json.dumps(results, default=str)
        return json_results

    finally:
        # Close the session
        session.close()

def handle_function(run,thread_id, queries_and_response,user,question):
    tools_to_call = run.required_action.submit_tool_outputs.tool_calls
    tools_output_array = []
    for each_tool in tools_to_call:
        tool_call_id = each_tool.id
        function_name = each_tool.function.name
        function_arg = each_tool.function.arguments
        print(f'tool: {each_tool}')
        print(f'Tool id: {tool_call_id}')
        print(f'function to call {function_name}')
        print(f'paramerters to use: {function_arg}')

        if function_name == 'query_details':
            arguments_str = each_tool.function.arguments
            arguments_dict = json.loads(arguments_str)
            query = arguments_dict['query']
            output = query_details(query, queries_and_response,user, thread_id,question)
            print('***QUERY***')
            print(query)
            print('***OUTPUT****')
            print(output)
            print(type(output))
            tools_output_array.append({"tool_call_id":tool_call_id,"output":output})

    client.beta.threads.runs.submit_tool_outputs(
        thread_id = thread_id,
        run_id = run.id,
        tool_outputs = tools_output_array
    )
    return query,output

def check_cancelled(task_id):
    # Re-query the RunningTasks object to ensure you have the latest state
    running_task = db.session.query(RunningTasks).filter_by(task_id=task_id).first()
    db.session.refresh(running_task)
    print(running_task)
    return running_task.cancelled

def ask_question(question,conversation_id,user,free_mode,task_id):
    # Re-query the RunningTasks object to ensure you have the latest state
    if check_cancelled(task_id):
        return 'question cancelled by user',0,0,0,thread_id,'question cancelled by user'

    
    # Initialize return variables with default values
    full_response = None
    prompt_tokens = 0
    completion_tokens = 0
    total_cost = 0
    thread_id = None
    queries_and_response = []
    # Load in the instructions
    with open("monstagpt/blueprints/gpt/templates/gpt/instructions/instructions.txt", "r") as f: 
        gpt_instructions = f.read() 

    try:
        assistant_id = 'asst_6CkGH87gzu0M7ZOpShuM4fRq'
        if free_mode:
            assistant_id = 'asst_KP9XtMkzZb1iClr6ZCzpPkBG'
        print(f'in ask question \n Here is the conversation_id: \n {conversation_id}')
        if not conversation_id:
            # Create a thread 
            thread = client.beta.threads.create()
            thread_id = thread.id
        else:
            print('using existing id')
            thread_id = conversation_id

        print(f'in ask question \n Here is the thread_id: \n {thread_id}')
        # print(f'here is the type of thread.id: {type(thread.id)}')
        print(f'here is the type of thread_id: {type(thread_id)}')

        if check_cancelled(task_id):
            return 'question cancelled by user',0,0,0,thread_id,'question cancelled by user'
        
        # Add the user's message to the thread
        client.beta.threads.messages.create(
            thread_id = thread_id,
            role='user',
            content = question
        )

        # Create a run
        run = client.beta.threads.runs.create(
            thread_id = thread_id,
            assistant_id = assistant_id,
            instructions = gpt_instructions
        )
        queries_and_response = []
        # Poll for the run to complete and retrieve the assistant messages
        while run.status not in ['completed', 'failed']:
            if check_cancelled(task_id):
                return 'question cancelled by user', 0, 0, 0, thread_id, 'question cancelled by user'

            if run.status == 'requires_action':
                try:
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tools_output_array = []
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.id
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        if function_name == 'query_details':
                            query = function_args['query']
                            output = query_details(query, queries_and_response, user, thread_id, question)
                            queries_and_response.append({'query': query, 'output': output})
                            tools_output_array.append({"tool_call_id": tool_call_id, "output": output})

                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tools_output_array
                    )
                except Exception as e:
                    print(f'Error in handling function: {e}')
                    run = client.beta.threads.runs.cancel(
                        thread_id=thread_id,
                        run_id=run.id
                    )
                    break

            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        if run.status == 'failed':
            run = client.beta.threads.runs.cancel(
                thread_id=thread_id,
                run_id=run.id
            )
            send_slack_message(slack_critical_webhook_url, f'GPT questions not working:\n {run.last_error}')

        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )

        assistant_messages_for_run = [
            message for message in messages
            if message.run_id == run.id and message.role == 'assistant'
        ]

        for message in assistant_messages_for_run:
            full_response = process_messages(message)

        if len(queries_and_response) == 0 and run.status != 'completed':
            run = client.beta.threads.runs.cancel(
                thread_id=thread_id,
                run_id=run.id
            )

        return full_response, prompt_tokens, completion_tokens, total_cost, thread_id, queries_and_response

    
    except Exception as e:
        print(f"An error occurred during ask_question execution: {e}")
        # Log the error and optionally set full_response to a meaningful error message
        full_response = "An error occurred while processing your request."
        print('*** This was the exception ***')
        print(type(e))
        print(e)
        run = client.beta.threads.runs.cancel(
            thread_id=thread_id,
            run_id=run.id
            )
        # Return the expected values, which will either be default values or actual outcomes based on the execution flow
        return full_response, prompt_tokens, completion_tokens, total_cost, thread_id, queries_and_response

    finally:
        # This block ensures that you always print the response and return values,
        # even if there was an exception.
        print("****THE RESPONSE*****")
        print(queries_and_response)
        # Return the expected values, which will either be default values or actual outcomes based on the execution flow
    # return full_response, prompt_tokens, completion_tokens, total_cost, thread_id, queries_and_response

# This file does nothing to save a conversation anywhere, so need to send a question and full_response and a thread id to a database. 
# later will also need to get the prompt and completion tokens and send them also

def get_model_name():

    return f' model is: '