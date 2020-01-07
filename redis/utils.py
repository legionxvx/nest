from functools import wraps
from http import HTTPStatus
from time import sleep

from flask import jsonify
from redis import RedisError
from redlock import RedLockError

from .. import logger
from .locking import LockFactory
from .session import RedisInstance


def locks(resource=None, max_tries=5, lock_args={}):
    resource = resource
    def decorator(f):
        nonlocal resource
        nonlocal lock_args
        if not(resource):
            resource = f.__name__
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                factory = LockFactory()
                with factory.create_lock(resource, **lock_args):
                    return f(*args, **kwargs)
            except (RedLockError):
                lock = factory.create_lock(resource)
                tries = 0
                while not(lock.acquire()) and not(tries >= max_tries):
                    logger.debug(f"Attempting to acquire lock "
                                 f"{tries+1}/{max_tries}")
                    sleep(5)
                    tries += 1
                else:
                    logger.debug("Giving up!")
                lock.release()
            except (ConnectionError):
                logger.critical("Cannot connect to redis!")
        return decorated_function
    return decorator

def greenlight(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            redis = RedisInstance()
            greenlight = redis.get("greenlight")
            if (greenlight == b"1"):
                return f(*args, **kwargs)
        except (RedisError):
            logger.error("Cannot connect to redis. Is the server running?")
            message = "Cannot determine greenlight status."
            return jsonify(message=message), HTTPStatus.INTERNAL_SERVER_ERROR

        message = "Endpoint is not accepting connections at this time."
        return jsonify(message=message), HTTPStatus.FORBIDDEN
    return decorated_function
