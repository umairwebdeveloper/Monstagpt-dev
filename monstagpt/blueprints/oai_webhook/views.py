from flask import Blueprint
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from lib.util_json import render_json
from monstagpt.extensions import csrf
from monstagpt.blueprints.oai_webhook.models import Oaistatus

oai_webhook = Blueprint("oai_webhook", __name__, template_folder="templates",url_prefix='/oai_webhook')

@oai_webhook.post('/test')
@csrf.exempt
def test():
     return('this is a test')

@oai_webhook.post("/event")
@csrf.exempt
def event():
    print('endpoint hit')
    if not request.json:
            return render_json(406, {"error": "Mime-type is not application/json"})

    data = request.json
    print('got the data')
    incident_name = data['incident']['name']
    incident_status = data['incident']['status'] 
    incident_id = data['incident']['id']

    print(incident_id,incident_name,incident_status)

    if incident_status == 'resolved':
        Oaistatus.delete_record(incident_id)
    else:
        Oaistatus.update_records(incident_id, incident_name, incident_status)

    return render_json(200, {"success": True})
