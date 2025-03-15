from loguru import logger
import time

class Camera(object):
    def __init__(self):
        logger.info("Камера запущена")

    def detect_graffiti(self):
        logger.info("Поиск граффити...")
        time.sleep(2)
