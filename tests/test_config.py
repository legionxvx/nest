import pytest

from nest.config import Config

def test_config():
    assert(Config() is not None)