from logging.config import fileConfig

from alembic import context
from sqlalchemy import URL, create_engine

from config import db_settings

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def run_migrations_online():
    settings = db_settings()
    url = URL.create(
        "mysql+pymysql",
        username=settings["user"],
        password=settings["password"],
        host=settings["hosts"][0],
        database=settings["database"],
        query={"charset": "utf8mb4"},
    )
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
