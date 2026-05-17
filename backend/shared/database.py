#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : database
from typing import Generator
from urllib.parse import quote_plus

from config.settings import settings

app_options = settings.app_options

database_type = app_options.get("database.type", "") or "sqlite"
database_url = ""
mydb = None
Base = None
engine = None
get_db = None
get_dbs = None

if database_type == "sqlite":
    from .sqliteorm.connect import sqlite_db

    mydb = sqlite_db
    Base = sqlite_db.Base
    sqlite_options = app_options.get("sqlite_options") or {}
    sqlite_name = sqlite_options.get("name") or "hyt.db"
    database_url = f"sqlite:///./db/{sqlite_name}"
    sqlite_db.init_session(database_url=database_url)
    engine = sqlite_db.engine
    get_db = sqlite_db.get_db
    get_dbs = sqlite_db.get_dbs
elif database_type == "pgsql":
    from .pgorm.connect import pgsql_db

    pgsql_options = app_options.get("pgsql_options") or {}
    password_encoded = quote_plus(str(pgsql_options.get("password", "")))
    user = pgsql_options.get("user", "postgres")
    host = pgsql_options.get("host", "127.0.0.1")
    port = pgsql_options.get("port", 5432)
    database = pgsql_options.get("database", "fan_ce_dev")
    connect_timeout = int(pgsql_options.get("connect_timeout", 5) or 5)
    database_url = f"postgresql+psycopg://{user}:{password_encoded}@{host}:{port}/{database}"
    mydb = pgsql_db
    pgsql_db.init_session(database_url, connect_args={"connect_timeout": connect_timeout})
    Base = pgsql_db.Base
    engine = pgsql_db.engine
    get_db = pgsql_db.get_db
    get_dbs = pgsql_db.get_dbs
else:
    raise RuntimeError(f"unsupported database.type: {database_type}. supported types: pgsql, sqlite")


class MyDBManager:
    """ 操作数据库 """
    def __init__(self):
        mydb.init_session(database_url)
        self.db_factory = mydb.session_local
        self.db = None

    def __enter__(self):
        self.db = self.db_factory()
        return self.db

    def __exit__(self, exc_type, exc_value, traceback):
        if self.db is not None:
            self.db.close()


def get_db3() -> Generator:
    """ 数据库连接对象 """
    with MyDBManager() as db:
        yield db
