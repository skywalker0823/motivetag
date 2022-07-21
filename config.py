import os
from dotenv import load_dotenv

load_dotenv()


class Config_dev(object):
    DEBUG = True
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    JSON_SORT_KEYS = False
    SECRET_KEY = os.urandom(8)
    ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
    ACCESS_SECRET_ID = os.getenv("ACCESS_SECRET_ID")
    DB = os.getenv("LOCAL_DB")


class Config_prodution(Config_dev):
    DEBUG = False
    DB = os.getenv("AWS_motivetag_DB")


class Config_AWS(Config_dev):
    DEBUG = False


config_sets = {
    'dev': Config_dev,
    'pro': Config_prodution,
    'aws': Config_AWS
}
