import logging
logger = logging.getLogger("nest")
logger.setLevel(logging.INFO)
from os.path import exists
from pathlib import Path

from yaml import safe_load
config_path = Path(__file__).parent / "config.yaml"
config = {}
if exists(config_path):
    with open(config_path, "r") as f:
        config = safe_load(f)

from .fastspring import FastSpring
from .fastspring.utils import bootstrap, get_products
# from .fastspring.events import Event, EventParser
from .mailchimp import Mailchimp
from .engines.redis import LockFactory, RedisInstance, locks, greenlight
from .engines.psql.engine import Engine
from .engines.psql.models import User, Product, Order
