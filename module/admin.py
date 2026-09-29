"""Who may review reports: the accounts in ADMIN_ACCOUNTS (Parameter Store
/motivetag/admin-accounts; see infra/README.md, "Reviewing reports")."""

from flask import current_app, session


def is_admin():
    account = session.get("account")
    return bool(account) and account in current_app.config["ADMIN_ACCOUNTS"]
