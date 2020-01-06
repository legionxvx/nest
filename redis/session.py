from os import environ
from redis import Redis

from .. import config
from ..types import Singleton

DEFAULT_HOST = config.get("RD_HOST") or environ.get("REDIS_HOST", "localhost")

class RedisInstance(Redis, metaclass=Singleton):

    def __init__(self, host=None):
        host = host or DEFAULT_HOST
        super().__init__(host=host)