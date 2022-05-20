

from flask import Flask, redirect, session, render_template as rt
from config import config_sets
from flask_socketio import SocketIO
socketio = SocketIO()


def create_app(config_name):
    app = Flask(__name__, static_folder="../static",static_url_path="/", template_folder="../templates")
    app.config.from_object(config_sets[config_name])
    from api.blueprints.api_member import api_member
    from api.blueprints.api_blocks import api_blocks
    from api.blueprints.api_tags import api_tags
    from api.blueprints.api_friends import api_friends
    from api.blueprints.api_message import api_message
    from api.blueprints.api_images import api_images
    from api.blueprints.api_notification import api_notification
    from api.blueprints.api_chat import api_chat
    from api.blueprints.api_tag_page import api_tag_page
    app.register_blueprint(api_member)
    app.register_blueprint(api_blocks)
    app.register_blueprint(api_tags)
    app.register_blueprint(api_friends)
    app.register_blueprint(api_message)
    app.register_blueprint(api_images)
    app.register_blueprint(api_notification)
    app.register_blueprint(api_chat)
    app.register_blueprint(api_tag_page)

    
    @app.route("/")
    def index():
        if session.get("account"):
            return redirect("/"+session["account"])
        else:
            return rt("index.html")


    @app.route("/tag/<tag_name>")
    def tag(tag_name):
        return rt("tag.html")


    socketio.init_app(app, cors_allowed_origins="*")
    return app