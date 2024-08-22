import logging
import sys


def get_logger(name=None):

    default = __name__
    debug_mode = hasattr(sys, 'gettrace') and sys.gettrace()

    if name:
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger(default)

    if debug_mode:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.ERROR)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S"))
    logger.addHandler(handler)

    return logger