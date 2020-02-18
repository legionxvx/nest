from json import load
from pathlib import Path

import pytest

from nest.engines.psql.engine import Engine
from nest.fastspring.events import (Order, Return, SubscriptionActivated,
                                    SubscriptionDeactivated, WebhookEvent)

@pytest.fixture(scope="module")
def engine():
    yield Engine()

@pytest.fixture(scope="module")
def session(engine):
    yield engine()

@pytest.fixture(scope="module")
def order_data():
    path = Path(__file__).parent / "test_orders"
    for file in path.glob("*.json"):
        pass
    
    with open(file, "r") as f:
        yield load(f)

@pytest.fixture(scope="module")
def return_data():
    path = Path(__file__).parent / "test_returns"
    for file in path.glob("*.json"):
        pass
    
    with open(file, "r") as f:
        yield load(f)

@pytest.fixture(scope="module")
def subscription_active_data():
    path = Path(__file__).parent / "test_subscription_activations"
    for file in path.glob("*.json"):
        pass
    
    with open(file, "r") as f:
        yield load(f)

@pytest.fixture(scope="module")
def subscription_inactive_data():
    path = Path(__file__).parent / "test_subscription_deactivations"
    for file in path.glob("*.json"):
        pass
    
    with open(file, "r") as f:
        yield load(f)

def test_event(order):
    data = {
        "id": "asdfghjkl",
        "live": False,
        "processed": False,
        "type": "order.completed",
        "created": 0
    }
    
    event = WebhookEvent(data)
    assert(event is not None)

@pytest.mark.skip(not(Engine().connected), reason="Cannot test without database.")
def test_order_event(session, order_data):
    ord = Order(order_data, session=session)

@pytest.mark.skip(not(Engine().connected), reason="Cannot test without database.")
def test_return_event(session, return_data):
    ret = Return(return_data)

@pytest.mark.skip(not(Engine().connected), reason="Cannot test without database.")
def test_subscription_active_event(session, subscription_active_data):
    sub = SubscriptionActivated(subscription_active_data, session=session)

@pytest.mark.skip(not(Engine().connected), reason="Cannot test without database.")
def test_subscription_active_event(session, subscription_inactive_data):
    sub = SubscriptionDeactivated(subscription_inactive_data, session=session)