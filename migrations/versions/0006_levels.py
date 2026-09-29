"""Levels rework (ADR 0015): daily exp caps, visit streaks and a new level curve.

Exp is converted so nobody's level changes: the old curve needed 25·n(n−1) exp for
level n, the new one 50·(n−1)². Each member keeps their level and their progress
through it. The previous release reads the converted exp with the old curve and
shows a somewhat higher level until the next deploy; the downgrade converts back.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29
"""

import math

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def old_total(level):
    return 25 * level * (level - 1)


def new_total(level):
    return 50 * (level - 1) ** 2


def old_level(exp):
    return int((math.sqrt(8 * exp / 50 + 1) + 1) / 2)


def new_level(exp):
    return math.isqrt(exp // 50) + 1


def convert(exp, level_of, from_total, to_total):
    """Same level, same share of the way to the next one."""
    exp = max(int(exp or 0), 0)
    level = level_of(exp)
    while from_total(level + 1) <= exp:  # guards against float rounding
        level += 1
    while level > 1 and from_total(level) > exp:
        level -= 1
    share = (exp - from_total(level)) / (from_total(level + 1) - from_total(level))
    return to_total(level) + round(share * (to_total(level + 1) - to_total(level)))


def convert_all(**curves):
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT member_id, exp FROM member WHERE exp > 0")).fetchall()
    for member_id, exp in rows:
        bind.execute(
            sa.text("UPDATE member SET exp=:exp WHERE member_id=:id"),
            {"exp": convert(exp, **curves), "id": member_id},
        )


def upgrade():
    op.execute(
        """CREATE TABLE exp_daily (
          member_id INT NOT NULL,
          day DATE NOT NULL,
          action VARCHAR(30) NOT NULL,
          count INT NOT NULL DEFAULT 0,
          PRIMARY KEY (member_id, day, action),
          KEY day (day),
          CONSTRAINT exp_daily_member FOREIGN KEY (member_id)
            REFERENCES member (member_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    op.execute("ALTER TABLE member ADD COLUMN last_active_day DATE NULL")
    op.execute("ALTER TABLE member ADD COLUMN streak INT NOT NULL DEFAULT 0")
    convert_all(level_of=old_level, from_total=old_total, to_total=new_total)


def downgrade():
    convert_all(level_of=new_level, from_total=new_total, to_total=old_total)
    op.execute("ALTER TABLE member DROP COLUMN streak")
    op.execute("ALTER TABLE member DROP COLUMN last_active_day")
    op.execute("DROP TABLE exp_daily")
