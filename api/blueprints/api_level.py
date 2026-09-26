from . import api_level
from flask import request, session
from data.data import Level


@api_level.route("/api/level", methods=["GET"])
def getting_current_exp():
    return
