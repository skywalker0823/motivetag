from . import api_level


@api_level.route("/api/level", methods=["GET"])
def getting_current_exp():
    return
