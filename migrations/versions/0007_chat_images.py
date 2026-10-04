"""Photos in chat: a message may carry one image (an S3 key, see api/v1/chats.py).

The previous release ignores the column and shows such a message as an empty bubble,
so a rollback keeps working.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-04
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE direct_message ADD COLUMN image VARCHAR(80) NULL")
    # /images/<key> checks who may see a chat photo by looking it up.
    op.execute("ALTER TABLE direct_message ADD KEY image (image)")


def downgrade():
    op.execute("ALTER TABLE direct_message DROP KEY image")
    op.execute("ALTER TABLE direct_message DROP COLUMN image")
