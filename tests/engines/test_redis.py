import pytest

from nest.engines import RedisEngine

def test_redis():
    engine = RedisEngine()
    assert(engine is not None)
    assert(engine.set("foo", "bar"))