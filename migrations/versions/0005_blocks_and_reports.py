"""Blocking members and reporting content (App Store Guideline 1.2, ADR 0014).

The previous release ignores the new tables and column, so a rollback keeps working
(it just shows hidden posts again and ignores blocks until the next deploy).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-29
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """CREATE TABLE member_block (
          blocker_id INT NOT NULL,
          blocked_id INT NOT NULL,
          created_at DATETIME NOT NULL,
          PRIMARY KEY (blocker_id, blocked_id),
          KEY blocked (blocked_id),
          CONSTRAINT member_block_blocker FOREIGN KEY (blocker_id)
            REFERENCES member (member_id) ON DELETE CASCADE,
          CONSTRAINT member_block_blocked FOREIGN KEY (blocked_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    # target_id points at block, block_comment, member or direct_message depending on
    # target_type; no foreign key, so a report outlives what it reported.
    op.execute(
        """CREATE TABLE report (
          report_id INT NOT NULL AUTO_INCREMENT,
          reporter_id INT NOT NULL,
          target_type VARCHAR(10) NOT NULL,
          target_id BIGINT NOT NULL,
          target_member_id INT NULL,
          reason VARCHAR(20) NOT NULL,
          detail VARCHAR(500) NULL,
          weight TINYINT NOT NULL DEFAULT 1,
          snapshot TEXT NULL,
          created_at DATETIME NOT NULL,
          status VARCHAR(10) NOT NULL DEFAULT 'open',
          handled_at DATETIME NULL,
          PRIMARY KEY (report_id),
          UNIQUE KEY one_per_reporter (reporter_id, target_type, target_id),
          KEY target (target_type, target_id, status),
          KEY status_created (status, created_at),
          CONSTRAINT report_reporter FOREIGN KEY (reporter_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    # Posts reported by enough members wait out of sight until someone reviews them.
    op.execute("ALTER TABLE block ADD COLUMN hidden TINYINT NOT NULL DEFAULT 0")


def downgrade():
    op.execute("ALTER TABLE block DROP COLUMN hidden")
    op.execute("DROP TABLE report")
    op.execute("DROP TABLE member_block")
