import pytest

from nest.types import Singleton

def test_singleton():
    class Dummy(metaclass=Singleton):
        pass

    d1, d2 = Dummy(), Dummy()
    assert(id(d1) == id(d2))
    assert(d1 is d2)