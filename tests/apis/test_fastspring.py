import pytest

from nest.apis.fastspring import FastSpring

@pytest.fixture(scope="module")
def session():
    yield FastSpring()

def test_fastspring(requests_mock, session):
    requests_mock.get(f"{session.prefix}/orders", json={"test":1})
    res = session.get("orders")
    json = res.json()