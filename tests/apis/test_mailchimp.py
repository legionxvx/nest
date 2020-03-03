import pytest

from nest.apis.mailchimp import Mailchimp


@pytest.fixture()
def session(scope="module"):
    yield Mailchimp()

def test_mailchimp(session):
    session.default_list = "Harrison Opted-In Promo List"
    res = session.get("members")
    assert(res.ok)

def test_mailchimp_get_members(session):
    session.default_list = "Harrison Opted-In Promo List"
    counter = 0
    for member in session.get_members():
        counter += 1
        if counter == 10:
            break

def test_mailchimp_get_member(session):
    session.default_list = "Harrison Opted-In Promo List"

    email = ""
    for member in session.get_members():
        email = member.get("email_address", "foo@bar.com")
        break
    
    res = session.get_member(email)
