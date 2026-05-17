# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/22 23:27
@Function: 
@version :  1.0
@Desc    :  None
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Generator


class MyDBManager:
    """ 操作数据库 """

    def __init__(self, session_local):
        self.db = session_local()

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()


class SqliteDb:
    def __init__(self, database_url=""):
        self.database_url = database_url
        self.session_local = None
        self.engine = None
        self.Base = declarative_base()

    def init_session(self, database_url="sqlite:///./db/test.db"):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=self.engine,
        )

    def init_db(self):
        self.Base.metadata.create_all(bind=self.engine)

    def get_dbs(self) -> Generator:
        db = self.session_local()
        return db

    def get_db(self) -> Generator[Session, None, None]:
        db = self.session_local()
        try:
            yield db
        finally:
            db.close()


sqlite_db = SqliteDb()
