from common.logged import LoggedClass, configure_logger
from robot.engine import Engine
from common.command import Command, CommandWithArguments
from broker import CommandReciever

class Robot(LoggedClass):
    def __init__(self):
        super().__init__()
        self.logger.info("Инициализация робота")
        self.engine = Engine()

        self.broker = CommandReciever()
        self.running = False

    def process_command(self, command: Command | CommandWithArguments):
        self.logger.info(f"Обработка команды: {command}")
        match command:
            case Command.MOVE_FORWARD:
                print("Вперёд")
                self.engine.forward(move_time=1)
            case Command.TURN_RIGHT:
                print("Направо")
                self.engine.turn_right()
            case Command.TURN_LEFT:
                print("Налево")
                self.engine.turn_left()
            case Command.STOP:
                print("Стоп")
                self.engine.stop()
    
    def start(self):
        self.logger.info("Запуск робота...")
        status = self.broker.connect(self.process_command)
        self.running = status
        while self.running:
            pass
    
    def stop(self):
        self.running = False
        self.logger.info("Остановка робота...")


if __name__ == "__main__":
    configure_logger()
    try:
        robot = Robot()
        robot.start()
    except KeyboardInterrupt:
        robot.stop()