import logging
from os import environ

from psycopg2 import OperationalError
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from nest.logging import Logger
from nest.types import Singleton

class SelfDestructingSession(Session):
    """A `scoped_session` that will automatically remove itself from 
    the Scoped Session registry when this wrapper object falls out of 
    scope.
    """
    def __init__(self, factory, session):
        self.__dict__ == session.__dict__
        self.factory = factory

    def __del__(self):
        self.factory.remove()

class PostgreSQLEngine(Engine, metaclass=Singleton):
    """An `Engine` connected a PostgreSQL database
    """
    DEFAULT_CONNECTION_INFO = {
        "drivername": "postgresql",
        "host": "localhost",
        "port": "5432",
        "username": "postgres",
        "password": "",
        "database": None,
    }
        
    def __init__(self, **kwargs):
        self.error_logger = logging.getLogger("nest")
        self.transaction_logger = logging.getLogger("nest.transaction")

        connection_info = kwargs.pop("connection_info", {})
        self.DEFAULT_CONNECTION_INFO.update(connection_info)

        try:
            meta = create_engine(
                URL(**self.DEFAULT_CONNECTION_INFO), 
                **kwargs
            )
            self.__dict__ = meta.__dict__
        except (SQLAlchemyError, OperationalError) as ex:
            self.error_logger.error(f"Could not create engine:{ex}")

        self.session_factory = sessionmaker(bind=self)
        self.scoped_session_factory = scoped_session(self.session_factory)

    def add_listener(self, event, func, *args, **kwargs):
        """Adds event callback function. List of events is available 

            :param event: Name of the event
            :param func: Callback function
            :param *args: Passed to event.listen
            :param **kwargs: Passed to event.listen
        """
        event.listen(self, event, func, *args, **kwargs)

    def remove_listener(self, event, func):
        """Removes event callback

            :param event: Name of the event
            :param func: Callback function
        """
        event.remove(self, event, func)

    def session(self, **kwargs):
        """Create a `Session` for querying the database

            :param **kwargs: Passed to `Session` constructor
        """
        return self.session_factory(**kwargs)

    def scoped_session(self, self_destruct=True, **kwargs):
        """Create a `scoped_session` for querying the database
            
            :param self_destruct=True: Returns a 
            `SelfDestructingSession` instead of a normal 
            `scoped_session`

            :param **kwargs: Passed to `Session` constructor
        """
        if self_destruct:
            return SelfDestructingSession(
                self.scoped_session_factory,
                self.scoped_session_factory(**kwargs),
            )
        return self.scoped_session_factory(**kwargs)
