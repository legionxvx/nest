import pytest

from nest.engines import PostgreSQLEngine
from nest.engines.psql.engine import SelfDestructingSession
from sqlalchemy.orm import Session

from nest.config import Config
from nest.logging import Logger

VALID_CONNECTION = False

@pytest.fixture(scope="module")
def engine():
    engine = PostgreSQLEngine()
    VALID_CONNECTION = engine.connected
    yield engine

@pytest.mark.skipif(not(VALID_CONNECTION), reason="Needs valid DB connection.")
def test_engine_callback_registration(engine):
    counter = 0
    def callback(*args, **kwargs):
        nonlocal counter
        counter += 1

    engine.add_listener("checkout", callback)
    with engine.connect():
        pass

    engine.remove_listener("checkout", callback)
    with engine.connect():
        pass

    assert counter == 1

@pytest.mark.skipif(not(VALID_CONNECTION), reason="Needs valid DB connection.")
def test_session_checkout(engine):
    session = engine.session()
    assert(isinstance(session, Session))

    session = engine.scoped_session()
    assert(isinstance(session, SelfDestructingSession))

    session = engine.scoped_session(self_destruct=False)
    assert(isinstance(session, Session))