from base64 import b64encode, urlsafe_b64encode
from hashlib import sha1
from os import environ, urandom
from random import choice

import pytest

from nest.apis.mailchimp import Mailchimp

SkipIfNoAuth = pytest.mark.skipif(
    not(
        environ.get("MAILCHIMP_AUTH_USER") and \
        environ.get("MAILCHIMP_AUTH_TOKEN")
    ), 
    reason="You must have Mailchimp API credentials to run these tests."
)

def random_str(length=16, safe=True):
    rv, bits = b"", urandom(length)
    if safe:
        rv = urlsafe_b64encode(bits)
    else:
        rv = b64encode(bits)
    return rv.decode("utf-8")


@pytest.fixture()
def session():
    session = Mailchimp()
    session.default_list = environ.get("DEFAULT_MAILCHIMP_LIST")
    yield session

@SkipIfNoAuth
def test_mailchimp_basic(session):
    for list_name, list_id in session.lists.items():
        session.default_list = list_name
        res = session.get("members")
        assert(list_id in res.url)
        assert(res.ok)

    session.default_list = random_str()
    res = session.get("members")
    assert(not(res.ok))


@SkipIfNoAuth
def test_mailchimp_get_members(session):
    counter, limit = 0, 30
    for member in session.get_members():
        counter += 1
        assert(member.get("list_id") == session.lists.get(session.default_list))
        if counter > limit:
            break

@SkipIfNoAuth
def test_mailchimp_get_member(session):
    email = ""
    for member in session.get_members():
        email = member.get("email_address", "foo@bar.com")
        break
    
    member = session.get_member(email)
    assert(member.get("list_id") == session.lists.get(session.default_list))