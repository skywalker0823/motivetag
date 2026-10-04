# 0013. Store chat messages and push them to members, instead of live rooms

- Status: Accepted
- Date: 2026-09-28

## Context

Chat worked like a phone call. Opening a chat created an in-memory Socket.IO room
keyed by the caller's socket id and waited; the other member only saw "想跟你聊天"
next to a name in the friends card (often folded) and had to open the chat to
"join". Nothing was stored, so anything said before the other side joined, while a
phone slept, or after a reconnect was lost. Presence kept one socket id per member,
so a second tab or a reconnect gave the member a new id that the room lookup did not
know, and the two sides could end up waiting in different rooms: the member saw the
other person "join" late, or never, although they were already typing.

People expect Messenger or Telegram: a list of conversations, history, messages that
arrive whether or not the other side is looking, unread counts, "已讀" and "正在輸入".

## Decision

- Messages are rows in `direct_message` (sender, recipient, content, sent_at,
  read_at), migration 0004. A conversation is the pair of members; there are no rooms.
- The browser sends with `POST /api/v1/chats/<account>/messages` (real status codes,
  friends only, e-mail verified, 1000 characters, 30 messages a minute). The server
  stores the message and pushes `chat:message` to the `member:<account>` room of both
  members, which every tab joins on connect.
- `GET /api/v1/chats` lists conversations with unread counts; `GET
  .../messages?before=<id>` pages history; `POST .../read` sets read_at and pushes
  `chat:read`. `chat:typing` goes browser → server → the friend's tabs over the socket.
- Presence counts tabs: a member is offline when their last socket disconnects.
- After a reconnect or when the page becomes visible, the browser reloads the list
  and open conversations, so pushes missed while disconnected are caught up.

## Consequences

- Nothing depends on both members being online or on socket ids; offline members
  find messages and a badge when they come back.
- Messages are personal data kept in the database and in backups (35 days after
  deletion); deleting an account deletes both sides of its conversations. The
  privacy policy must say so.
- The pushes still come from one process ([0008](0008-single-gunicorn-worker.md)); with
  several workers, `socketio.emit` needs the Redis message queue. The stored messages
  themselves already work with any number of workers.
- Blocking members (ADR 0010 phase 1) must refuse sending in both directions.
- Photos (migration 0007, 2026-10-04) follow [0007](0007-direct-browser-uploads-to-s3.md):
  `POST /api/v1/chats/<account>/images` signs an upload to a key `dm_<sender>_<random>`,
  the browser sends the file to S3, then the message carries the key (checked: mine,
  uploaded, used once). `/images/dm_…` opens only for the two members and admins.
  A photo that was uploaded but never sent stays in the bucket; an S3 lifecycle rule
  can clean those up if they ever add up.

## Alternatives considered

- **Keep rooms but fix the socket-id bugs**: still loses everything said while the
  other side is away, which is what people notice most.
- **Send messages over the socket**: fewer requests, but no status codes or
  acknowledgements without building them, and a message sent during a reconnect
  disappears silently. HTTP send + socket push is what the mobile app will want too.
- **A hosted chat service (Stream, Sendbird)**: fast to build, but a monthly bill and
  a third party holding private messages.

## Revisit when

Chat volume makes the conversation query slow (then keep a `conversation` table with
the last message and unread counts), or we need group chats or images in chat.
