import pytest

from nest.config import Config

@pytest.fixture(scope="module")
def config():
    config = Config()
    config.parser.read_string(
        """
        [nest]
        errorlogLevel=critical
        transactionlogLevel=critical

        FS_AUTH_USER=foo
        FS_AUTH_PASS=bar

        MC_AUTH_USER=foo
        MC_AUTH_TOKEN=bar

        [nest:postgresql]
        host=localhost
        port=5432
        username=foo
        password=bar
        database=baz

        [nest:redis]
        host=foo
        port=6379
        db=bar

        [nest:redis1]
        host=foo
        port=6379
        db=bar
        """
    )
    config.reload()
    yield config

def test_config_nest(config):
    assert(config.errlogLevel == "critical")
    assert(config.translogLevel == "critical")

    assert(isinstance(config.fastspring_auth, tuple))
    assert(config.fastspring_auth[0] == "foo")
    assert(config.fastspring_auth[1] == "bar")

    assert(isinstance(config.mailchimp_auth, tuple))
    assert(config.mailchimp_auth[0] == "foo")
    assert(config.mailchimp_auth[1] == "bar")

def test_config_psql(config):
    info = {
        "host": "localhost",
        "port": 5432,
        "username": "foo",
        "password": "bar",
        "database": "baz"
    }
    assert(config.postgres_connection_info == info)

def test_config_redis(config):
    assert(len(config.redis_node_list) == 2)
    
    redis_node = {
        "host": "foo",
        "port": 6379,
        "db": "bar"
    }
    for info in config.redis_node_list:
        assert(info == redis_node)