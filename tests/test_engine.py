import pytest

from nest import Engine

@pytest.fixture
def engine():
    return Engine()

def test_connect(engine):
    assert engine.connected