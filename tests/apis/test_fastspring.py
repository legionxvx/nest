from base64 import b64encode, urlsafe_b64encode
from os import urandom
from urllib.parse import urlencode, urljoin

import pytest

from nest.apis.fastspring import FastSpring
from nest.apis.fastspring.events import EventParser, Order
from nest.engines.psql import PostgreSQLEngine


def random_str(length=16, safe=True):
    rv, bits = b"", urandom(length)
    if safe:
        rv = urlsafe_b64encode(bits)
    else:
        rv = b64encode(bits)
    return rv.decode("utf-8")

@pytest.fixture()
def engine(postgresql):
    connection_info = {
        "port": postgresql.info.port,
        "database": postgresql.info.dbname
    }
    yield PostgreSQLEngine(connection_info=connection_info)

@pytest.fixture()
def database(engine):
    session = engine.session()
    yield session
    session.close()

@pytest.fixture(scope="module")
def session():
    yield FastSpring()

def test_session_hooks(session):
    counter = 0
    def callback(*args, **kwargs):
        nonlocal counter
        counter += 1

    session.hooks["response"] = callback
    session.request("GET", "")

    session.hooks.pop("response", None)
    session.request("GET", "")

    assert(counter == 1)

def test_fastspring_get_products(session):
    products = []
    for product, info in session.get_products(blacklist=["bundle"]).items():
        products.append(product)
        for key in ["price", "aliases"]:
            assert(key in info.keys())
        assert(product in info.get("aliases"))

    if len(products) > 1:
        p1 = products[0]
        p2 = products[1]
        r1 = random_str()
        r2 = random_str()
        product_info = session.get_products(
            filter=[p1, p2, random_str()], 
            blacklist=["bundle"]
        )

        for p in [p1, p2]:
            assert(p in product_info)
        
        for p in [r1, r2]:
            assert(p not in product_info)

    product_info = session.get_products(filter=[random_str()])
    assert(product_info == {})

def test_fastspring_get_orders(session):
    params = {
        "scope": "live",
        "status": "completed",
        "begin": "2020-02-27",
        "end": "2020-02-28",
        "limit": 50
    }
    for order in session.get_orders(params=params):
        break

def test_fastspring_get_events(session):
    for event in session.get_events("processed", params={"days":2}):
        break

def test_fastspring_update_event(session):
    for event in session.get_events("processed", params={"days":1}):
        res = session.update_event(
            event.get("id"), 
            params={
                "processed": True
            }
        )
        assert(res.get("processed"))
        break

def test_order_event(session, database):
    for event in session.get_events("processed", params={"days":2}):
        order = Order(event, session=database)
        database.add(order.model)
        database.commit()
        break
