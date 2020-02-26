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
from nest.engines.psql.models import Base, Order, Product, Return, User
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

@pytest.fixture()
def session(engine):
    session = engine.session()
    yield session
    session.close()

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

def test_order_returning(session):
    order = Order(reference=random_str(), total=999)

    session.add(order)
    session.commit()

    query = session.query(Order).filter(Order.returned)
    assert(not(order.returned))
    assert(order not in query.all())

    ret = Return(reference=random_str(), amount=order.total)
    ret.order = order

    session.add(ret)
    session.commit()

    query = session.query(Order).filter(Order.returned)
    assert(order.returned)
    assert(order in query.all())

    query = session.query(Return).filter(Return.partial == False)
    assert(not(ret.partial))
    assert(ret in query.all())

    ret.amount = order.total/2
    session.add(ret)
    session.commit()

    query = session.query(Order).filter(Order.returned)
    assert(not(order.returned))
    assert(order not in query.all())

    query = session.query(Return).filter(Return.partial == True)
    assert(ret.partial)
    assert(ret in query.all())

def test_user_hybrid_property_products(session):
    user = User(
        email=f"{random_str()}@{random_str()}.com",
        first=random_str(),
        last=random_str()
    )

    product = Product(name=random_str())
    order = Order(reference=random_str(), total=999)
    order.user = user
    order.products.append(product)
    assert(product in user.products)

    ret = Return(reference=random_str(), amount=order.total/2)
    ret.order = order

    assert(product in user.products)
    ret.amount = order.total

    session.add(ret)
    session.commit()
    
    query = session.query(User).filter(User.products.contains([product.name]))
    assert(product not in user.products)
    assert(user not in query.all())

    ret.amount = order.total/2
    session.add(ret)
    session.commit()

    query = session.query(User).filter(User.products.contains([product.name]))
    assert(product in user.products)
    assert(user in query.all())

def test_user_hybrid_meth_owns_any_in_set(session):
    user = User(
        email=f"{random_str()}@{random_str()}.com",
        first=random_str(),
        last=random_str()
    )

    set_name = random_str()
    product = Product(name=random_str(), set=set_name)

    order = Order(reference=random_str())
    order.user = user
    order.products.append(product)

    session.add(order)
    session.commit()

    query = session.query(User).filter(User.owns_any_in_set(set_name))
    assert(user.owns_any_in_set(set_name))
    assert(user in query.all())
