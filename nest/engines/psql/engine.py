import logging
from os import environ

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.event import contains, listen, remove
from sqlalchemy.exc import (InvalidRequestError, OperationalError,
                            SQLAlchemyError)
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from nest.engines.psql.models import Base
from nest.types import Singleton


class SelfDestructingSession(Session):
    """A `Session` that will automatically remove itself from
    the Scoped Session registry when this wrapper object falls out of
    scope.
    """
    def __init__(self, factory, session):
        self.__dict__ == session.__dict__
        self.factory = factory

    def __del__(self):
        self.factory.remove()

class PostgreSQLEngine(Engine):
    """An `Engine` connected a PostgreSQL database"""
    DEFAULT_CONNECTION_INFO = {
        "drivername": "postgresql",
        "host": "localhost",
        "port": "5432",
        "username": "postgres",
        "password": "",
        "database": None,
    }
    def __init__(self, url=None, **kwargs):
        self.error_logger = logging.getLogger("nest")
        self.transaction_logger = logging.getLogger("nest.transaction")

        if not(url):
            connection_info = kwargs.pop("connection_info", {})
            connection_info.pop("drivername", None)
            self.DEFAULT_CONNECTION_INFO.update(connection_info)

        try:
            meta = create_engine(
                url or URL(**self.DEFAULT_CONNECTION_INFO),
                **kwargs
            )
            self.__dict__.update(meta.__dict__)
        except (SQLAlchemyError) as ex:
            self.error_logger.error(f"Could not create engine: {ex}")

        try:
            with self.connect():
                self.connected = True
        except (OperationalError) as ex:
            self.connected = False
            self.error_logger.error(f"Cannot connect to database: {ex}")

        self.session_factory = sessionmaker(bind=self)
        self.scoped_session_factory = scoped_session(self.session_factory)

        Base.metadata.create_all(self)

    def add_listener(self, event, func, *args, **kwargs):
        """Adds event callback function. List of events is available

            :param event: Name of the event
            :param func: Callback function
            :param *args: Passed to event.listen
            :param **kwargs: Passed to event.listen
        """
        if not(contains(self, event, func)):
            try:
                listen(self, event, func, *args, **kwargs)
            except (InvalidRequestError) as ex:
                message = f"Cannot assign listener to `{event}`: {ex}"
                self.error_logger.error(message)

    def remove_listener(self, event, func):
        """Removes event callback

            :param event: Name of the event
            :param func: Callback function
        """
        if contains(self, event, func):
            try:
                remove(self, event, func)
            except (InvalidRequestError) as ex:
                message = f"Cannot remove listener from `{event}`: {ex}"
                self.error_logger.error(message)

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
