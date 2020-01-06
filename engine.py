from os import environ

from psycopg2 import OperationalError
from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from nest.models import Base

from . import logger, config


HOST = config.get("DB_HOST") or environ.get("DB_HOST", "localhost")
PORT = config.get("DB_PORT") or environ.get("DB_PORT", "5432")
DATABASE = config.get("DB_NAME") or environ.get("DB_DATABASE", "postgres")

class Singleton(type):

    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance

class Engine(metaclass=Singleton):

    def __init__(self, url=None, auth=None, echo=False, poolclass=None):
        auth = auth or config.get("DB_AUTH") or (
                environ.get("PG_USER"), 
                environ.get("PG_PASS")
            )

        usr = auth[0] or "foo"
        pwd = auth[1] or "bar"

        connection_info = {
            "drivername": "postgresql",
            "host": HOST,
            "port": PORT,
            "username": usr,
            "password": pwd,
            "database": DATABASE
        }
        
        self.url = url or URL(**connection_info)
        self.connected = False
        logger.debug(f"Connecting Engine @ {self.url}")

        try:
            pc = poolclass or NullPool
            self.engine = create_engine(self.url, echo=echo, poolclass=pc)
            Base.metadata.create_all(self.engine)
            self.connected = True
        except (SQLAlchemyError, OperationalError) as error:
            logger.critical(error)

        self.session_factory = sessionmaker(bind=self.engine)

        @event.listens_for(self.session_factory, "after_commit")
        def receive_after_commit(session):
            logger.debug("Received commit")

    def __call__(self, **kwargs):
        session = self.session_factory(**kwargs)
        logger.debug(f"Session @ {session}")
        return session

    def set_echo(self, yn):
        self.engine.echo = bool(yn)

    def get_echo(self):
        return self.engine.echo