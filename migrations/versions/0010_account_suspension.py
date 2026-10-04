"""Account suspension: the owner can lock a member out for a while or for good.

The previous release ignores both columns, so a rollback keeps working (suspended
members could sign in again until the release is redeployed).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-05
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    # NULL or a past time: not suspended. module/suspension.py PERMANENT means for good.
    op.execute(
        """ALTER TABLE member
          ADD COLUMN suspended_until DATETIME NULL,
          ADD COLUMN suspended_reason VARCHAR(200) NULL"""
    )


def downgrade():
    op.execute("ALTER TABLE member DROP COLUMN suspended_reason, DROP COLUMN suspended_until")
