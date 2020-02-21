import logging
from os import environ

from psycopg2 import OperationalError
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from nest.logging import Logger
from nest.types import Singleton


class PostgreSQLEngine(Engine, metaclass=Singleton):
    """docstring here

        :param Engine: 
        :param metaclass=Singleton: 
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
            self.error_logger.error("Could not create engine: ", ex)

        self.session_factory = sessionmaker(bind=self)
        self.scoped_session_factory = scoped_session(self.session_factory)

    def setup_callbacks(self):
        """docstring here

            :param self: 
        """
        @event.listens_for(self.session_factory, "after_commit")
        def receive_after_commit(session):
            self.transaction_logger.debug("@after_commit => Recieved commit.")

    def session(self, **kwargs):
        """docstring here

            :param self: 
            :param **kwargs: 
        """
        return self.session_factory(**kwargs)

    def scoped_session(self, **kwargs):
        """docstring here
        
            :param self: 
            :param **kwargs: 
        """   
        return self.scoped_session_factory(**kwargs)
