from os import environ

from redlock import RedLockFactory

from nest import config
from nest.types import Singleton

# DEFAULT_HOST = config.get("RD_HOST") or environ.get("REDIS_HOST", "localhost")
# DEFAULT_PORT = config.get("RD_PORT") or environ.get("REDIS_PORT", 6379)
# DEFAULT_DB = config.get("RD_DB") or environ.get("REDIS_DB", 0)

class LockFactory(RedLockFactory, metaclass=Singleton):
    def __init__(self, host=None, port=None, db=None, conn_info=None):
        conn_info = conn_info or [
            { 
                "host": host or "localhost", 
                "port": port or "6379", 
                "db": db or 0
            }
        ]
        super().__init__(connection_details=conn_info)