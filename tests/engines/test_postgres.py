import pytest

from nest.engines import PostgreSQLEngine

def test_engine():
    args = {
        "connection_info": {
            "password": "secret",
        },
        "echo": True
    }
    engine = PostgreSQLEngine(**args)
    assert(engine is not None)

    session = engine.session()
    assert(session)
    session = engine.scoped_session()
    assert(session)