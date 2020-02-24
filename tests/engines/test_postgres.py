from datetime import datetime

import pytest
from sqlalchemy.dialects.postgresql import psycopg2
from sqlalchemy.orm import Session

from nest.config import Config
from nest.engines import PostgreSQLEngine
from nest.engines.psql.engine import SelfDestructingSession
from nest.logging import Logger

from testing.postgresql import Postgresql

@pytest.fixture(scope="module")
def engine():
    with Postgresql() as psql:
        yield PostgreSQLEngine(url=psql.url())

def test_engine_basic(engine):
    assert(isinstance(engine.dialect, psycopg2.dialect))

    for row in engine.execute("SELECT current_timestamp"):
        for date in row:
            assert(isinstance(date, datetime))

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

def test_session_checkout(engine):
    session = engine.session()
    assert(isinstance(session, Session))

    session = engine.scoped_session()
    assert(isinstance(session, SelfDestructingSession))

    session = engine.scoped_session(self_destruct=False)
    assert(isinstance(session, Session))

def test_engine_execute(engine):
    for row in engine.execute("SELECT current_timestamp"):
        for date in row:
            assert(isinstance(date, datetime))
