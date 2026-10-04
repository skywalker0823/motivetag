"""Personal card colours and cover image, and each member's look for the site.

A row only exists once a member changes something; the previous release ignores the
table, so a rollback keeps working (everyone sees the default look again).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-05
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    # Colours are "#rrggbb" (checked by the app), NULL for the default.
    op.execute(
        """CREATE TABLE member_profile (
          member_id INT NOT NULL,
          card_accent CHAR(7) NULL,
          cover_from CHAR(7) NULL,
          cover_to CHAR(7) NULL,
          name_color CHAR(7) NULL,
          cover_img VARCHAR(40) NULL,
          ui_mode VARCHAR(10) NULL,
          ui_accent VARCHAR(10) NULL,
          ui_text VARCHAR(10) NULL,
          updated_at DATETIME NOT NULL,
          PRIMARY KEY (member_id),
          CONSTRAINT member_profile_member FOREIGN KEY (member_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )


def downgrade():
    op.execute("DROP TABLE member_profile")
