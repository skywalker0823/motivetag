from flask import current_app, request, session

from api.blueprints.api_images import BUCKET_NAME, s3
from data.data import Member

from . import error, login_required, v1


@v1.route("/account", methods=["DELETE"])
@login_required
def delete_account():
    """Deletes the signed-in member and their content (App Store Guideline 5.1.1(v)).

    The password is asked again so a borrowed, still signed-in browser cannot do it.
    """
    body = request.get_json(silent=True) or {}
    member_id = session["member_id"]
    if not Member.password_matches(member_id, body.get("password")):
        return error("wrong_password", "密碼不正確", 403)

    image_keys = Member.delete(member_id)
    if image_keys is None:
        return error("not_found", "找不到這個帳號", 404)
    session.clear()
    remove_images(image_keys)
    return {"deleted": True}


def remove_images(keys):
    """Best effort: the database rows are already gone, so the images are unreachable
    through the site either way; a failure here is logged, not shown to the member."""
    if not keys or not BUCKET_NAME:
        return
    try:
        s3.delete_objects(
            Bucket=BUCKET_NAME,
            Delete={"Objects": [{"Key": key} for key in keys], "Quiet": True},
        )
    except Exception as exc:  # noqa: BLE001 - never fail a deletion over leftover files
        current_app.logger.warning("could not delete images %s: %s", keys, exc)
