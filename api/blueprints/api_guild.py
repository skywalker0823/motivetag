from . import api_guild  # noqa: F401 - re-exported for api/__init__.py


# import redis
# rds =  redis.Redis(host='redis',port=6379)


# rds.set("count",0)

# @api_guild.route("/api_guild")
# def get_guild():
#     if request.args.get("count"):
#         rds.incr("count")
#         return rds.get("count")
