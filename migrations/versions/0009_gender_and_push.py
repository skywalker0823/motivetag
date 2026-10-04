"""A gender a member may show next to their name, and Web Push subscriptions.

The previous release ignores both, so a rollback keeps working (no icons, no pushes).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-05
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    # NULL: not shown. Values are checked by the app (api/v1/profile.py GENDERS).
    op.execute("ALTER TABLE member_profile ADD COLUMN gender VARCHAR(10) NULL")
    # One row per browser or phone that agreed to notifications (api/v1/push.py).
    op.execute(
        """CREATE TABLE push_subscription (
          subscription_id INT NOT NULL AUTO_INCREMENT,
          member_id INT NOT NULL,
          endpoint VARCHAR(500) NOT NULL,
          p256dh VARCHAR(200) NOT NULL,
          auth VARCHAR(100) NOT NULL,
          created_at DATETIME NOT NULL,
          PRIMARY KEY (subscription_id),
          UNIQUE KEY endpoint (endpoint),
          KEY member (member_id),
          CONSTRAINT push_subscription_member FOREIGN KEY (member_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )


def downgrade():
    op.execute("DROP TABLE push_subscription")
    op.execute("ALTER TABLE member_profile DROP COLUMN gender")
