import pytest

from nest.logging import Logger
from nest.config import Config

@pytest.fixture(scope="module")
def config():
    config = Config()
    config.parser.read_string(
        """
        [nest]
        errorlogLevel=critical
        transactionlogLevel=critical
        """
    )
    config.reload()
    yield config

@pytest.fixture(scope="module")
def logger(config):
    yield Logger(config)

def test_logger_basic(config, logger):
    assert(logger.errorlogLevel == logger.LOG_LEVELS.get(config.errlogLevel))
    assert(logger.translogLevel == logger.LOG_LEVELS.get(config.translogLevel))
    for fn in [
        logger.exception, 
        logger.debug, 
        logger.info, 
        logger.warning, 
        logger.error, 
        logger.critical
    ]:
        fn("")