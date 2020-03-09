from base64 import b64encode, urlsafe_b64encode
from os import path, urandom
from time import sleep

import pytest
from pytest_redis.factories import redisdb
from redis.lock import LockError
from redlock import RedLockError

from nest.engines.redis import LockFactory, RedisEngine

SkipIfNoRedis = pytest.mark.skipif(
    not(path.exists("/usr/bin/redis-server")), 
    reason="You must have Redis installed."
)

def random_str(length=16, safe=True):
    rv, bits = b"", urandom(length)
    if safe:
        rv = urlsafe_b64encode(bits)
    else:
        rv = b64encode(bits)
    return rv.decode("utf-8")

@pytest.fixture()
def engine(redisdb):
    yield RedisEngine(connection_pool=redisdb.connection_pool)

@pytest.fixture()
def lock_factory(redisdb):
    connection_details = [
        {
            "connection_pool": redisdb.connection_pool
        }
    ]
    yield LockFactory(connection_details=connection_details)

@SkipIfNoRedis
def test_redis_engine_basic(engine):
    key, value = random_str(), random_str()
    assert(engine is not None)
    assert(engine.set(key, value))
    assert(engine.get(key) == value.encode())

@SkipIfNoRedis
def test_redis_engine_lock(engine):
    res = random_str()
    with engine.lock(res, blocking_timeout=5):
        with pytest.raises(LockError):
            # LockError is thrown after timeout
            with engine.lock(res, blocking_timeout=1):
                pass

@SkipIfNoRedis
def test_redis_engine_pubsub(engine):
    ps = engine.pubsub()
    chan = random_str()

    # Produces three messages which we will read from
    ps.subscribe(chan)

    data = random_str()
    engine.publish(chan, data)

    ps.unsubscribe()

    res = ps.get_message()
    assert(res.get("channel") == chan.encode())
    assert(res.get("type") == "subscribe")
    assert(res.get("data") == 1)

    res = ps.get_message()
    assert(res.get("channel") == chan.encode())
    assert(res.get("data") == data.encode())

    res = ps.get_message()
    assert(res.get("channel") == chan.encode())
    assert(res.get("type") == "unsubscribe")

@SkipIfNoRedis
def test_lock_factory(lock_factory):
    lf = lock_factory

    resource = random_str()
    with lf.create_lock(resource):
        with pytest.raises(RedLockError):
            # Locks only throw RedLockError on enter context
            with lf.create_lock(resource):
                pass
