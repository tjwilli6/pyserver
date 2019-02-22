from srv_logger import getlogger
from config import Config
import os

config = Config() 

opts = dict(config)
opts['__name__'] = __name__

opts['FNAME'] = '{}/.pyserver/log/pyserver.log'.format(os.getenv('HOME'))

config['FNAME'] = opts['FNAME']
config.write()

logger = getlogger(**opts)

logger.warn("This package uses threading and I'm too lazy to worry about synchronizing log messages!")
logger.warn("Be aware that log messages may be out of order!")


def set_logging(level=config.get("LOGLEVEL"),logfile=config.get("FNAME",None), **kwargs):
    logger = getlogger(LOGLEVEL=level,FNAME=logfile,__name__=__name__,**kwargs)
    config['LOGLEVEL'] = level
    if not logfile in (None,"None",""):
        config['FNAME'] = logfile
    config.write() 