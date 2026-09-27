"""Let a member be deleted: their comments go with them, tags they created stay.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE block_comment DROP FOREIGN KEY block_comment_ibfk_2")
    op.execute(
        "ALTER TABLE block_comment ADD CONSTRAINT block_comment_ibfk_2 FOREIGN KEY (member_id)"
        " REFERENCES member (member_id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE tag DROP FOREIGN KEY tag_ibfk_1")
    op.execute(
        "ALTER TABLE tag ADD CONSTRAINT tag_ibfk_1 FOREIGN KEY (create_by)"
        " REFERENCES member (member_id) ON DELETE SET NULL"
    )


def downgrade():
    op.execute("ALTER TABLE tag DROP FOREIGN KEY tag_ibfk_1")
    op.execute(
        "ALTER TABLE tag ADD CONSTRAINT tag_ibfk_1 FOREIGN KEY (create_by)"
        " REFERENCES member (member_id)"
    )
    op.execute("ALTER TABLE block_comment DROP FOREIGN KEY block_comment_ibfk_2")
    op.execute(
        "ALTER TABLE block_comment ADD CONSTRAINT block_comment_ibfk_2 FOREIGN KEY (member_id)"
        " REFERENCES member (member_id)"
    )
