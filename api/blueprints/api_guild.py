

from flask import request, session

from . import api_guild

import redis
# rds =  redis.Redis(host='0.0.0.0',port=6379)


# rds.set("count",0)

# @api_guild.route("/api_guild")
# def get_guild():
#     if request.args.get("count"):
#         rds.incr("count")
#         return rds.get("count")

