from os import environ
from redis import Redis

from nest import config
from nest.types import Singleton

# DEFAULT_HOST = config.get("RD_HOST") or environ.get("REDIS_HOST", "localhost")

class RedisInstance(Redis, metaclass=Singleton):

    def __init__(self, host=None):
        host = host or "localhost"
        super().__init__(host=host)