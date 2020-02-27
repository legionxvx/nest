import logging
from functools import wraps
from os import environ

from redis import Redis

from nest.types import Singleton


class RedisEngine(Redis, metaclass=Singleton):
    """docstring here
    """
    DEFAULT_CONNECTION_DETAILS = {
        "host": "localhost",
        "port": 6379,
        "db": 0
    }
    def __init__(self, **kwargs):
        self.DEFAULT_CONNECTION_DETAILS.update(kwargs)
        super().__init__(**self.DEFAULT_CONNECTION_DETAILS)
        self.logger = logging.getLogger("nest")
