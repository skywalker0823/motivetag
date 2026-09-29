import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _secret_key():
    key = os.getenv("SECRET_KEY")
    if key:
        return key
    # Without a shared key every worker/restart signs sessions differently, so set SECRET_KEY in .env.
    print("WARNING: SECRET_KEY is not set, using a temporary random key")
    return secrets.token_hex(32)


def db_settings():
    """Connection settings shared by the app and Alembic migrations."""
    return {
        "hosts": [
            h
            for h in (os.getenv("AWS_motivetag_DB"), os.getenv("DB_BK1"), os.getenv("DB_BK2"))
            if h
        ],
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DATABASE", "motivetag"),
    }


class Config_dev(object):
    DEBUG = True
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    JSON_SORT_KEYS = False
    SECRET_KEY = _secret_key()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    DB = os.getenv("AWS_motivetag_DB")
    # E-mail verification (module/email_verification.py): off unless EMAIL_FROM is set.
    EMAIL_FROM = os.getenv("EMAIL_FROM")
    # Local development: log e-mails (with their links) instead of sending them.
    MAIL_SUPPRESS = os.getenv("MAIL_SUPPRESS") == "1"
    SES_REGION = os.getenv("SES_REGION") or os.getenv("AWS_REGION")
    # Cloudflare Turnstile on sign-up (module/turnstile.py): off unless both are set.
    TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY")
    TURNSTILE_SECRET = os.getenv("TURNSTILE_SECRET")
    # Accounts that may review reports on /admin (comma-separated, no spaces).
    ADMIN_ACCOUNTS = frozenset(a for a in os.getenv("ADMIN_ACCOUNTS", "").split(",") if a)


class Config_prodution(Config_dev):
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    SESSION_COOKIE_SECURE = True
    DB = os.getenv("AWS_motivetag_DB")


class Config_AWS(Config_prodution):
    pass


config_sets = {"dev": Config_dev, "pro": Config_prodution, "aws": Config_AWS}
