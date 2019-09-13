import logging
from logging.handlers import TimedRotatingFileHandler

trfh = TimedRotatingFileHandler(f'logs/{__name__}.log', when='midnight', 
                                backupCount=14)

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