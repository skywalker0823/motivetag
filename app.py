import os

from api import create_app, socketio

# Defaults to production settings; set FLASK_CONFIG=dev for local development.
app = create_app(os.getenv("FLASK_CONFIG", "pro"))

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000, debug=False)  # noqa: S104 - runs inside a container

# Local setup, tests and migrations: see "Development" in README.md.
