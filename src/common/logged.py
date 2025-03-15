import sys
from loguru import logger

class LoggedClass(object):
    def __init__(self):
        self.logger = logger.bind(classname=self.__class__.__name__)


def configure_logger():
    logger_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "[{extra[classname]}] <level>{message}</level>"
    )
    logger.remove()
    logger.add(
        sys.stdout,
        format=logger_format
    )