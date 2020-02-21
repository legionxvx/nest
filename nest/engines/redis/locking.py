from os import environ

from redlock import RedLockFactory

from nest.types import Singleton


class LockFactory(RedLockFactory, metaclass=Singleton):
    """docstring here

        :param RedLockFactory: 
        :param metaclass=Singleton: 
    """
    DEFAULT_CONNECTION_DETAILS = [
        { 
            "host": "localhost", 
            "port": 6379, 
            "db": 0,
        },
    ]
    def __init__(self, **kwargs):
        conn_info = kwargs.pop("connection_details", [])
        self.DEFAULT_CONNECTION_DETAILS.extend(conn_info)
        super().__init__(self.DEFAULT_CONNECTION_DETAILS)
