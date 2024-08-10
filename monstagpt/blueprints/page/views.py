from flask import Blueprint
from flask import render_template
from flask_httpauth import HTTPBasicAuth
from flask import current_app
from flask import redirect
from flask import url_for
import ast
from bs4 import BeautifulSoup
import requests

page = Blueprint("page", __name__, template_folder="templates")

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    users_str = current_app.config["BASIC_AUTH_CREDS"]
    users = ast.literal_eval(users_str)
    if username in users and users[username] == password:
        return username
    
# @page.before_request
# @auth.login_required
# def before_request():
#     """ Protect all of the gpt endpoints. """
#     pass    

@page.get("/")
# @auth.login_required
def home():
    # return render_template("page/home.html")
    return redirect(url_for("user.login"))

@page.get("/support")
def support():
    # URL of the page you want to embed
    target_url = 'https://contact.appmonsta.ai/support'  # Replace with the actual URL
    
    # Fetch the page content
    response = requests.get(target_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract the specific div with the class you mentioned
    specific_content = soup.find('div', class_='kartra_helpdesk_sidebar_body_wrapper')
    
    if specific_content:
        # Render the content in your template
        return render_template('proxy_template.html', content=specific_content)
    else:
        return "The specified content was not found on the page."

@page.get("/terms")
# @auth.login_required
def terms():
    return render_template("page/terms.html")


@page.get("/privacy")
# @auth.login_required
def privacy():
    return render_template("page/privacy.html")

@page.get("/healthcheck")
def healthcheck():
    return "ok"

@page.get("/test")
# @auth.login_required
def test():
    return "test"
