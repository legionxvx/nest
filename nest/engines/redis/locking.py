from os import environ

from redlock import RedLockFactory

from nest.types import Singleton


class LockFactory(RedLockFactory, metaclass=Singleton):
    """Redis lock factory.
    """
    DEFAULT_CONNECTION_DETAILS = [
        {
            "host": "localhost",
            "port": 6379,
            "db": 0,
        },
    ]
    def __init__(self, **kwargs):
        kwargs["connection_details"] = kwargs.get(
            "connection_details",
            self.DEFAULT_CONNECTION_DETAILS
        )
        super().__init__(**kwargs)
