from crypt import methods
from flask import request,session
from . import api_tag_page


@api_tag_page.route("/api/tag_page",methods=["GET"])
def get_tag_datas():
    key = request.args.get("keyword")
    return {"ok":True}