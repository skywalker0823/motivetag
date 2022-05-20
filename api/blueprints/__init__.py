from flask import Blueprint

api_blocks = Blueprint('block', __name__, template_folder="templates")
api_chat = Blueprint('chat', __name__, template_folder="templates")
api_friends = Blueprint('friends', __name__, template_folder="templates")
api_images = Blueprint('images', __name__, template_folder="templates")
api_member = Blueprint('member', __name__, template_folder="templates")
api_message = Blueprint('message', __name__, template_folder="templates")
api_notification = Blueprint('notification', __name__, template_folder="templates")
api_tags = Blueprint('tags', __name__, template_folder="templates")
api_tag_page = Blueprint('tag_page', __name__, template_folder="templates")


