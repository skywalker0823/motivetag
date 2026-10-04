import mimetypes
import os

from dotenv import load_dotenv
from flask import Flask, redirect, request, session
from flask import render_template as rt
from flask_socketio import SocketIO

from config import config_sets

socketio = SocketIO()
load_dotenv()
# Not in every system's MIME table; browsers want it for the PWA manifest.
mimetypes.add_type("application/manifest+json", ".webmanifest")


def init_sentry(config_name):
    """Report unhandled errors to Sentry when SENTRY_DSN is set (only production sets it)."""
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment="production" if config_name == "pro" else config_name,
        release=os.getenv("GIT_SHA") or None,
        send_default_pii=False,
        # Errors only; performance tracing would use up the free quota.
        traces_sample_rate=0,
    )


def init_suspension(app):
    """A suspended member's open sessions end on their next request (module/suspension.py)."""
    from flask import redirect as go

    @app.before_request
    def end_suspended_session():
        member_id = session.get("member_id")
        if member_id is None or request.endpoint in ("static", "healthz"):
            return None
        from module import suspension

        state = suspension.current(member_id)
        if state is None:
            return None
        session.clear()
        if request.path.startswith("/api/"):
            return {"error": {"code": "suspended", "message": suspension.message(state)}}, 401
        return go("/")


def create_app(config_name):
    init_sentry(config_name)
    app = Flask(
        __name__, static_folder="../static", static_url_path="/", template_folder="../templates"
    )
    app.config.from_object(config_sets[config_name])
    from data.data import release_connection

    app.teardown_appcontext(release_connection)

    from api.assets import init_assets
    from api.metrics import init_metrics

    init_assets(app)
    init_metrics(app)
    init_suspension(app)
    from api.blueprints.api_blocks import api_blocks
    from api.blueprints.api_bricks import api_bricks
    from api.blueprints.api_chat import api_chat
    from api.blueprints.api_friends import api_friends
    from api.blueprints.api_guild import api_guild
    from api.blueprints.api_images import api_images
    from api.blueprints.api_level import api_level
    from api.blueprints.api_member import api_member
    from api.blueprints.api_message import api_message
    from api.blueprints.api_notification import api_notification
    from api.blueprints.api_tag_page import api_tag_page
    from api.blueprints.api_tags import api_tags
    from api.blueprints.api_vote import api_vote

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
    app.register_blueprint(api_guild)

    from api.v1 import v1

    app.register_blueprint(v1)

    @app.route("/healthz")
    def healthz():
        # Also proves the database answers, so deploy checks and uptime checks see it.
        from data.data import Member

        try:
            Member.ping()
        except Exception:
            return {"ok": False}, 503
        return {"ok": True}

    @app.route("/")
    def index():
        if session.get("account"):
            return redirect("/" + session["account"])
        else:
            from module import invites, turnstile
            from module.urls import public_base_url

            site_key = app.config["TURNSTILE_SITE_KEY"] if turnstile.enabled() else None
            inviter = invites.inviter(request.args.get("invite"))
            return rt(
                "index.html",
                turnstile_site_key=site_key,
                inviter=inviter["account"] if inviter else None,
                base_url=public_base_url(),
            )

    # Privacy policy and terms (App Store Guideline 5.1.1; ADR 0010 phase 1).
    LEGAL_UPDATED = "2026 年 10 月 5 日"

    @app.route("/privacy")
    def privacy():
        return rt(
            "privacy.html",
            contact_email=app.config["CONTACT_EMAIL"],
            updated=LEGAL_UPDATED,
        )

    @app.route("/terms")
    def terms():
        return rt("terms.html", contact_email=app.config["CONTACT_EMAIL"], updated=LEGAL_UPDATED)

    # The service worker must live at the root to control every page, and must not
    # be cached long, or a fixed version would take a year to arrive.
    @app.route("/sw.js")
    def service_worker():
        response = app.send_static_file("sw.js")
        response.headers["Cache-Control"] = "no-cache"
        return response

    # Files at the root would otherwise be taken for a member's page (/<account>).
    @app.route("/manifest.webmanifest")
    def manifest():
        return app.send_static_file("manifest.webmanifest")

    @app.route("/admin")
    def admin_page():
        from flask import abort

        from module.admin import is_admin

        if not is_admin():
            abort(404)
        return rt("admin.html")

    @app.route("/tag/<tag_name>")
    def tag(tag_name):
        if session.get("account"):
            return rt("tag.html")
        else:
            return redirect("/")

    @app.route("/tag/<tag_name>/<brick_id>")
    def brick(tag_name, brick_id):
        if session.get("account"):
            return rt("brick.html")
        else:
            return redirect("/")

    # Unset means same-origin only; list extra origins comma-separated in SOCKETIO_CORS_ORIGINS.
    cors_origins = os.getenv("SOCKETIO_CORS_ORIGINS")
    socketio.init_app(app, cors_allowed_origins=cors_origins.split(",") if cors_origins else None)
    return app


# test
