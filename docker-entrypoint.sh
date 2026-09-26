#!/bin/sh
set -e

# Bring the schema up to date before serving traffic.
alembic upgrade head

# One worker: chat presence lives in process memory (see api/blueprints/api_chat.py).
exec gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
    -b 0.0.0.0:3000 -w 1 app:app
