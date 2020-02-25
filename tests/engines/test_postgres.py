from base64 import b64encode, urlsafe_b64encode
from datetime import datetime
from os import urandom

import pytest
from sqlalchemy.dialects.postgresql import psycopg2
from sqlalchemy.orm import Session
from testing.postgresql import Postgresql

from nest.config import Config
from nest.engines import PostgreSQLEngine
from nest.engines.psql.engine import SelfDestructingSession
from nest.engines.psql.models import Base, User, Order, Product, Return
from nest.logging import Logger


def random_str(length=16, safe=True):
    rv, bits = b"", urandom(length)
    if safe:
        rv = urlsafe_b64encode(bits)
    else:
        rv = b64encode(bits)
    return rv.decode("utf-8")

@pytest.fixture(scope="module")
def engine():
    with Postgresql() as psql:
        yield PostgreSQLEngine(url=psql.url())

def test_engine_basic(engine):
    assert(isinstance(engine.dialect, psycopg2.dialect))

    for proxy in engine.execute("SELECT current_timestamp"):
        for date in proxy:
            assert(isinstance(date, datetime))

    for table in Base.metadata.sorted_tables:
        for proxy in engine.execute(f"SELECT * FROM {table.fullname}"):
            pass

@pytest.mark.parametrize("model, ctor_args", [
    (User, {
        "email": f"{random_str()}@{random_str()}.com",
        "first": random_str(),
        "last": random_str()
    }),

    (Order, {
        "reference": random_str(),
        "user_id": 1,
    }),

    (Return, {
        "reference": random_str(),
        "amount": 999,
        "order_id": 1
    }),

    (Product, {
        "name": random_str(),
    }),
])
def test_models(engine, model, ctor_args):
    session = engine.session()

    obj = model(**ctor_args)

    session.add(obj)
    session.commit()
    for table in Base.metadata.sorted_tables:
        if table.fullname != model.__tablename__:
            continue

        for key in table.columns.keys():
            assert(hasattr(obj, key))
            value = getattr(obj, key)
            if not(key in ctor_args):
                default = table.columns[key].default
                if default:
                    assert(value == default.arg)
    session.close()

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
