import pytest

from nest.fastspring.events import WebhookEvent

def test_webhook_event_construction():
    data = {
        "id": "asdfghjkl",
        "live": False,
        "processed": False,
        "type": "order.completed",
        "created": 0
    }
    
    event = WebhookEvent(data)
    assert(event is not None)