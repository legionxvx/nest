import pytest

from os import urandom
from base64 import b64encode

from nest.engines import LockFactory

from redlock import RedLockError

def test_lock_factory():
    lf = LockFactory()
    
    resource = b64encode(urandom(16)).decode()
    with lf.create_lock(resource):
        with pytest.raises(RedLockError):
            # Locks only throw RedLockError on enter context
            with lf.create_lock(resource):
                pass