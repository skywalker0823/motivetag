"""Direct messages: chat is stored, so it reaches people who are offline or on another tab.

The previous release keeps its in-memory chat and ignores this table, so a rollback
keeps working (messages sent in the meantime just stay in the table).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-28
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    # One row per message. A conversation is the pair of members; read_at marks when
    # the recipient saw it (read receipts and unread counts).
    op.execute(
        """CREATE TABLE direct_message (
          message_id BIGINT NOT NULL AUTO_INCREMENT,
          sender_id INT NOT NULL,
          recipient_id INT NOT NULL,
          content TEXT NOT NULL,
          sent_at DATETIME NOT NULL,
          read_at DATETIME NULL,
          PRIMARY KEY (message_id),
          KEY sender_recipient (sender_id, recipient_id, message_id),
          KEY recipient_sender (recipient_id, sender_id, message_id),
          KEY recipient_unread (recipient_id, read_at),
          CONSTRAINT direct_message_sender FOREIGN KEY (sender_id)
            REFERENCES member (member_id) ON DELETE CASCADE,
          CONSTRAINT direct_message_recipient FOREIGN KEY (recipient_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )


def downgrade():
    op.execute("DROP TABLE direct_message")
