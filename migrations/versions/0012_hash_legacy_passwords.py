"""Hash the passwords still stored in plain text.

Members from before password hashing kept a plain-text password until their next
sign-in (Member.sign_in upgraded it then); anyone who never came back still had one,
in the database and in every backup. Each is replaced by its hash, so the same
password still signs in.

The previous release accepts hashes too, so a rollback keeps working. The downgrade
cannot bring plain text back and does nothing.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-24
"""

import sqlalchemy as sa
from alembic import op
from werkzeug.security import generate_password_hash

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT member_id, password FROM member"
            " WHERE password NOT LIKE 'scrypt:%' AND password NOT LIKE 'pbkdf2:%'"
        )
    ).fetchall()
    for member_id, password in rows:
        bind.execute(
            sa.text("UPDATE member SET password = :hash WHERE member_id = :id"),
            {"hash": generate_password_hash(password), "id": member_id},
        )


def downgrade():
    pass
