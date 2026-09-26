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
    ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
    ACCESS_SECRET_ID = os.getenv("ACCESS_SECRET_ID")
    DB = os.getenv("AWS_motivetag_DB")


class Config_prodution(Config_dev):
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    SESSION_COOKIE_SECURE = True
    DB = os.getenv("AWS_motivetag_DB")


class Config_AWS(Config_prodution):
    pass


config_sets = {
    'dev': Config_dev,
    'pro': Config_prodution,
    'aws': Config_AWS
}
