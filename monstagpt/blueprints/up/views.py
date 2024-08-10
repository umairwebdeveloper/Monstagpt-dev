from flask import Blueprint

from monstagpt.extensions import db
from monstagpt.initializers import redis

up = Blueprint("up", __name__, template_folder="templates", url_prefix="/up")


@up.get("/")
def index():
    return ""


@up.get("/databases")
def databases():
    redis.ping()
    db.engine.execute("SELECT 1")
    return ""
