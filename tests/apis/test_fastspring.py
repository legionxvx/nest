import pytest

from nest.apis.fastspring import FastSpring

def test_fastspring():
    session = FastSpring()
    assert(session is not None)