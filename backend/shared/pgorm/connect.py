# -*- coding: utf-8 -*-
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class PgDb:
    def __init__(self, database_url=""):
        self.database_url = database_url
        self.session_local = None
        self.engine = None
        self.Base = Base

    def init_session(self, database_url, connect_args=None):
        self.database_url = database_url
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args or {},
        )
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


pgsql_db = PgDb()
