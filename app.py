from api import create_app, socketio

app = create_app("dev")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000)
