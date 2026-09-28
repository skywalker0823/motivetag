"""E-mail verification: when each member confirmed their address, and one-time links.

Members who joined before this count as verified. The previous release ignores the
new column and table, so a rollback keeps working.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-28
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE member ADD COLUMN email_verified_at DATETIME NULL")
    op.execute("UPDATE member SET email_verified_at = COALESCE(first_signup, CURRENT_DATE())")
    # Only a SHA-256 of each link's token is stored, so a database leak cannot verify.
    op.execute(
        """CREATE TABLE email_token (
          token_hash CHAR(64) NOT NULL,
          member_id INT NOT NULL,
          created_at DATETIME NOT NULL,
          expires_at DATETIME NOT NULL,
          PRIMARY KEY (token_hash),
          KEY member_created (member_id, created_at),
          KEY created_at (created_at),
          CONSTRAINT email_token_member FOREIGN KEY (member_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )


def downgrade():
    op.execute("DROP TABLE email_token")
    op.execute("ALTER TABLE member DROP COLUMN email_verified_at")
