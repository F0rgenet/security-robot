from common.logged import LoggedClass
import time


class Engine(LoggedClass):
    def __init__(self):
        super().__init__()
        self.logger.info("Инициализация двигателя")

    def forward(self, move_time: float):
        self.logger.info("Начало движения вперёд...")
        time.sleep(move_time)
        self.logger.success("Движение вперёд завершено")

    def turn_left(self):
        self.logger.info("Поворот налево...")

    def turn_right(self):
        self.logger.info("Поворот направо...")

    def stop(self):
        self.logger.info("Остановка двигателя...")