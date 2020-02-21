import logging
from logging.config import dictConfig

from colorlog import ColoredFormatter, StreamHandler


class Logger(object):

    LOG_LEVELS = {
        "critical": logging.CRITICAL,
        "error":    logging.ERROR,
        "warning":  logging.WARNING,
        "info":     logging.INFO,
        "debug":    logging.DEBUG
    }

    error_fmt = (r"%(purple)s%(asctime)s %(yellow)s[%(process)d] "
                 r"%(white)s[%(name)s] %(log_color)s[%(levelname)s] "
                 r"%(reset)s%(message)s")
    datefmt = r"[%Y-%m-%d %H:%M:%S %z]"

    def __init__(self, cfg):
        self.error_logger = logging.getLogger("nest")
        self.transcation_logger = logging.getLogger("nest.transaction")
        self.init(self.error_logger, self.transcation_logger)
        self.cfg = cfg
        self.setup(self.cfg)

    @classmethod
    def init(cls, *args):
        for logger in args:
            logger.propagate = False
            logger.handlers = []

    def setup(self, cfg=None):
        if cfg:
            self.cfg = cfg

        self.loglevel = self.LOG_LEVELS.get(
                self.cfg.loglevel.lower(), 
                logging.INFO
            )
        self.error_logger.setLevel(self.loglevel)
        self.transcation_logger.setLevel(logging.INFO)

        handler = StreamHandler()
        formatter = ColoredFormatter(self.error_fmt, self.datefmt)
        handler.setFormatter(formatter)
        self.error_logger.addHandler(handler)
        self.transcation_logger.addHandler(handler)

    def critical(self, msg, *args, **kwargs):
        self.error_logger.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.error_logger.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.error_logger.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.error_logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.error_logger.debug(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.error_logger.exception(msg, *args, **kwargs)

    def log(self, level, messsage, *args, **kwargs):
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.INFO)
        self.error_logger.log(level, messsage, *args, **kwargs)

    def transaction(self, level, messsage, *args, **kwargs):
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.INFO)
        self.transcation_logger.log(level, messsage, *args, **kwargs)
