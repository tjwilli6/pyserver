from srv_logger import getlogger
from config import Config

config = Config() 

opts = dict(config)
opts['__name__'] = __name__
logger = getlogger(**opts)

logger.warn("This package uses threading and I'm too lazy to worry about synchronizing log messages!")
logger.warn("Be aware that log messages may be out of order!")
logger.debug("Reading configuration from '{}'".format(config.filename))