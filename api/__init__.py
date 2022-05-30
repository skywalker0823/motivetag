

from flask import Flask, redirect, session, render_template as rt
from config import config_sets
from flask_socketio import SocketIO
import redis
import os
from dotenv import load_dotenv
socketio = SocketIO()
load_dotenv()



def create_app(config_name):
    app = Flask(__name__, static_folder="../static",static_url_path="/", template_folder="../templates")
    cache = redis.Redis(host='redis', port=6379)
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
    from api.blueprints.api_vote import api_vote
    from api.blueprints.api_level import api_level
    from api.blueprints.api_bricks import api_bricks

    app.register_blueprint(api_member)
    app.register_blueprint(api_blocks)
    app.register_blueprint(api_tags)
    app.register_blueprint(api_friends)
    app.register_blueprint(api_message)
    app.register_blueprint(api_images)
    app.register_blueprint(api_notification)
    app.register_blueprint(api_chat)
    app.register_blueprint(api_tag_page)
    app.register_blueprint(api_vote)
    app.register_blueprint(api_level)
    app.register_blueprint(api_bricks)


    GOOGLE_OAUTH2_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    
    @app.route("/")
    def index():
        if session.get("account"):
            return redirect("/"+session["account"])
        else:
            return rt("index.html", google_oauth2_client_id=GOOGLE_OAUTH2_CLIENT_ID)


    @app.route("/tag/<tag_name>")
    def tag(tag_name):
        if session.get("account"):
            return rt("tag.html")
        else:
            return redirect("/")

    @app.route("/tag/<tag_name>/<brick_id>")
    def brick(tag_name,brick_id):
        if session.get("account"):
            return rt("brick.html")
        else:
            return redirect("/")



    socketio.init_app(app, cors_allowed_origins="*")
    return app