from sqlalchemy.engine.url import URL
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from nest.models import Base

DB_INFO = {
    'drivername': 'postgres',
    'host': '',
    'port': '',
    'username': '',
    'password': '',
    'database': ''
}

class Engine(object):

    def __init__(self, URL=URL(**DB_INFO), echo=True):
        self.engine = create_engine(URL, echo=echo)

        Base.metadata.create_all(self.engine)

        self.session_factory  = sessionmaker(bind=self.engine)
        self.session_registry = scoped_session(self.session_factory)

    def new_session(self):
        """Checkout a new session from the registry
        
        Returns:
            [sqlalchemy.orm.session.Session] -- A newly checked out
                                                session
        """
        #call the session registry
        self.session = self.session_registry()
        return self.session

    def remove(self):
        """Threads that call this method will have their local session
           dropped from the registry.
        """
        self.session_registry.remove()

TheEngine = Engine()