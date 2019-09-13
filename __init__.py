import logging
from logging.handlers import TimedRotatingFileHandler

formatter = logging.Formatter("[%(threadName)14s %(asctime)s %(relativeCreated)6d %(funcName)14s] - %(message)s")

trfh = TimedRotatingFileHandler('logs/%s.log' % __name__, when='midnight', backupCount=14)
trfh.setFormatter(formatter)

loggers = {
    __name__:logging.INFO,
    'sqlalchemy.orm':logging.INFO,
    'sqlalchemy.dialects':logging.INFO,
    'sqlalchemy.engine':logging.WARN
}

for k,v in loggers.items():
    logger = logging.getLogger(k)
    logger.addHandler(trfh)
    logger.setLevel(v)