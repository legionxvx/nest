from os import environ

from sqlalchemy.engine.url import URL
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, event

from . import logger
from nest.models import Base

class Engine(object):

    def __init__(self, url=None, echo=False):
        conn_info = {
            "drivername": "postgresql",
            "host": environ.get("PG_HOST"),
            "port": environ.get("PG_PORT"),
            "username": environ.get("PG_USER"),
            "password": environ.get("PG_PASS"),
            "database": environ.get("PG_DATABASE")
        }

        self.url = url or URL(**conn_info)

        try:
            logger.info(f"Creating engine with metadata {Base.metadata}")
            self.engine = create_engine(self.url, echo=echo, poolclass=NullPool)
            Base.metadata.create_all(self.engine)
        except (SQLAlchemyError) as error:
            logger.critical(f"Cannot create engine: {error}")

        self.session_factory  = sessionmaker(bind=self.engine)
        self.session_registry = scoped_session(self.session_factory)

    def new_session(self):
        """Checkout a new session from the registry

        Returns:
            [sqlalchemy.orm.session.Session] -- A newly checked out
                                                session
        """
        #call the session registry
        logger.debug("Checked out new database session.")
        return self.session_registry()

    def remove(self):
        """Threads that call this method will have their local session
           dropped from the registry.
        """
        self.session_registry.remove()

    def set_echo(self, yn):
        self.engine.echo = bool(yn)

TheEngine = Engine()

@event.listens_for(TheEngine.session_factory, 'after_commit')
def receive_after_commit(session):
    logger.debug("Received commit.")