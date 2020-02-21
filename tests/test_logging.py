import pytest

from nest.logging import Logger
from nest.config import Config

def test_logger():
    cfg = Config()
    logger = Logger(cfg)
    logger.critical("1")