from base64 import b64encode, urlsafe_b64encode
from datetime import datetime, timedelta
from os import path, urandom, environ
from urllib.parse import urlencode, urljoin

import pytest

from nest.apis.fastspring import FastSpring
from nest.apis.fastspring.events import (
    EventParser, 
    Order, 
    Return, 
    SubscriptionActivated, 
    SubscriptionDeactivated, 
    WebhookEvent
)
from nest.engines.psql import PostgreSQLEngine

SkipIfNoAuth = pytest.mark.skipif(
    not(environ.get("FS_AUTH_USER") and environ.get("FS_AUTH_PASS")), 
    reason="You must have PostgreSQL 12 in order to run these tests."
)

SkipIfNoPsql = pytest.mark.skipif(
    not(path.exists("/usr/lib/postgresql/12/bin/pg_ctl")), 
    reason="You must have PostgreSQL 12 in order to run these tests."
)

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

@SkipIfNoAuth
def test_session_hooks(session):
    counter = 0
    def callback(*args, **kwargs):
        nonlocal counter
        counter += 1
    session.hooks["response"] = callback
    session.get("/")
    session.hooks.pop("response")
    session.get("/")
    assert(counter == 1)

@SkipIfNoAuth
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

@SkipIfNoAuth
@pytest.mark.parametrize("params", [
    (
        {
            "scope": "live",
            "status": "completed",
            "begin": "2020-01-01",
            "end": "2020-01-02",
            "limit": 20
        }
    ),
    (
        {
            "scope": "test",
            "status": "completed",
            "begin": "2020-01-02",
            "end": "2020-01-03",
            "limit": 20
        }
    ),
    (
        {
            "scope": "live",
            "status": "failed",
            "begin": "2020-01-04",
            "end": "2020-01-05",
            "limit": 20
        }
    ),
    (
        {
            "scope": "live",
            "status": "completed",
            "begin": "2020-01-01",
            "end": "2020-03-01",
            "returns": True,
            "limit": 20
        }
    ),
])
def test_fastspring_get_orders(session, params):
    begin = params.get("begin")
    begin = datetime.strptime(begin, "%Y-%m-%d")

    end = params.get("end")
    end = datetime.strptime(end, "%Y-%m-%d")

    limit = params.get("limit")

    counter = 0
    for order in session.get_orders(params=params):
        counter += 1
        status = params.get("status")
        scope = params.get("scope")

        if scope:
            if scope == "live":
                assert(order.get("live"))
            else:
                assert(not(order.get("live")))

        if status:
            if status == "completed":
                assert(order.get("completed"))
            elif status in ["failed", "canceled"]:
                assert(not(order.get("completed")))

        if params.get("returns"):
            for ret in order.get("returns"):
                assert(ret.get("amountInPayoutCurrency") > 0)

        date = datetime.utcfromtimestamp(order.get("changedInSeconds"))
        assert(begin < date < end)

        # Add +10 to make sure we jump into pagination  at least a
        # little bit
        if counter > limit + 10:
            break

@SkipIfNoAuth
@pytest.mark.parametrize("event_type, params", [
    ("processed", {"days":1}),
    ("unprocessed", {"begin": 0})
])
def test_fastspring_get_events(session, event_type, params):
    delta = timedelta(days=params.get("days", 0))
    begin = datetime.utcnow() - delta
    end = datetime.utcnow()

    counter, limit = 0, 20
    for event in session.get_events(event_type, params=params):
        counter += 1
        if event_type == "processed":
            assert(event.get("processed"))
        else:
            assert(not(event.get("processed")))

        if counter > limit:
            break

@SkipIfNoAuth
def test_fastspring_update_event(session):
    counter, limit = 0, 20
    for event in session.get_events("processed", params={"days": 1}):
        counter += 1
        res = session.update_event(event.get("id"), params={"processed": True})
        assert(res.get("processed"))

        if counter > limit:
            break

@SkipIfNoAuth
@SkipIfNoPsql
def test_event_parser(session, database):
    type_map = {
        "order.completed": Order,
        "return.created": Return,
        "subscription.activated": SubscriptionActivated,
        "subscription.deactivated": SubscriptionDeactivated,
    }

    generator = session.get_events("processed", params={"days":1})
    for event in EventParser(generator, session=database):
        if event.type in type_map.keys():
            assert(isinstance(event, type_map.get(event.type)))