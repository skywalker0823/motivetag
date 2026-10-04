"""A record of what admins did on /admin (suspensions, level changes, notices...).

The previous release ignores the table, so a rollback keeps working.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-05
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    # The admin and target are kept as account names, not foreign keys: the record
    # must outlive deleted accounts.
    op.execute(
        """CREATE TABLE admin_log (
          log_id INT NOT NULL AUTO_INCREMENT,
          admin VARCHAR(50) NOT NULL,
          action VARCHAR(30) NOT NULL,
          target VARCHAR(50) NULL,
          detail VARCHAR(500) NULL,
          created_at DATETIME NOT NULL,
          PRIMARY KEY (log_id),
          KEY created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )


def downgrade():
    op.execute("DROP TABLE admin_log")
