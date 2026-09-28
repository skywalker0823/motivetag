# 0008. One gunicorn worker, because chat presence lives in memory

- Status: Accepted (known limitation)
- Date: 2026-09-26

## Context

Online status is kept in module-level dictionaries in `api/blueprints/api_chat.py`
(chat messages are stored in MySQL since [0013](0013-stored-direct-messages.md)). Two worker processes (or two servers) would each have
their own copy, so users on different workers could not see or call each other.

## Decision

Run **one** gunicorn worker with the gevent-websocket worker class
(`docker-entrypoint.sh`). gevent gives that one process many concurrent
connections (HTTP and Socket.IO), which is enough for current traffic.

## Consequences

- Simple and correct for chat.
- CPU-bound work blocks everyone; anything slow must stay out of the request path
  (one reason for [0007](0007-direct-browser-uploads-to-s3.md)).
- Presence changes, incoming calls and new notifications are pushed through a
  Socket.IO room per member (`member:<account>`); the clients only re-check every
  30–60 s as a fallback. With several workers those emits need the Redis message
  queue too.
- Horizontal scaling is not possible until this changes, which is why
  [0001](0001-single-ec2-with-docker-compose.md) is a single server.

## Alternatives considered

- **Redis for presence plus Flask-SocketIO's Redis message queue** — the standard
  fix, and the planned one; it adds a service to run.
- **Sticky sessions** — would keep a user on one worker but still split presence.

## Revisit when

A single process runs out of CPU, or we need more than one server. Then: move
presence to Redis, enable the Socket.IO message queue, raise the worker count.
