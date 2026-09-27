from flask import request, session

from api.blueprints.api_blocks import with_extras
from data.data import Block
from module import rules

from . import error, login_required, v1


@v1.route("/posts/explore", methods=["GET"])
@login_required
def explore():
    """Everyone's newest public and anonymous posts, for members whose own feed is quiet.

    Same post shape as GET /api/blocks; page with ?offset=<posts already shown>.
    """
    offset = rules.integer(request.args.get("offset", "0"))
    if offset is None or offset < 0:
        return error("bad_offset", "offset 需為 0 以上的整數", 400)
    posts = Block.explore(offset)
    return {"data": with_extras(posts, session["member_id"])}
