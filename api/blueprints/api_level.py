from crypt import methods
from . import api_level
from flask import request, session
from data.data import Level






@api_level.route("/api/level",methods=["GET"])
def getting_current_exp():
    return


#提升~(皆為針對自己)
@api_level.route("/api/level",methods=["POST"])
def exp_upping():
    data = request.get_json()
    exp = data["exp"]
    member_id = session.get("member_id")
    result = Level.exp_up(member_id,exp)
    if result==1:
        return {"ok":result}
    return {"error":"exp modify fail"}

#提升~(針對被按讚或是爛做調整)


# @api_level.route("/api/level", methods=["DELETE"])
# def exp_downing():
#     return
