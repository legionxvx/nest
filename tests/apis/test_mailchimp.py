import pytest

from nest.apis.mailchimp import Mailchimp

def test_mailchimp():
    session = Mailchimp()
    assert(session is not None)