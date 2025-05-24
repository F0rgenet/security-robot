from common.logged import LoggedClass
import RPi.GPIO as GPIO
import time

from enum import Enum

class WheelState(Enum):
    FORWARD = "forward"
    REVERSE = "reverse"
    STOP = "stop"

class Wheel(Enum):
    LEFT = "left"
    RIGHT = "right"

class Engine(LoggedClass):
    def __init__(self):
        super().__init__()
        self.logger.info("Инициализация двигателя")
        self.IN1 = 12
        self.IN2 = 13
        self.IN3 = 20
        self.IN4 = 21
        self.ENA = 6
        self.ENB = 26

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.IN1, GPIO.OUT)
        GPIO.setup(self.IN2, GPIO.OUT)
        GPIO.setup(self.IN3, GPIO.OUT)
        GPIO.setup(self.IN4, GPIO.OUT)
        GPIO.setup(self.ENA, GPIO.OUT)
        GPIO.setup(self.ENB, GPIO.OUT)
    
    def control_wheel(self, wheel: Wheel, wheel_state: WheelState):
        self.logger.info(f"Контроль колеса {wheel}: {wheel_state}")
        pins = (self.IN1, self.IN2) if wheel == Wheel.LEFT else (self.IN4, self.IN3)
        if wheel_state == WheelState.FORWARD:
            GPIO.output(pins[0], GPIO.HIGH)
        elif wheel_state == WheelState.REVERSE:
            GPIO.output(pins[1], GPIO.HIGH)
        else:
            GPIO.output(pins[0], GPIO.LOW)
            GPIO.output(pins[1], GPIO.LOW)
        

    def forward(self, move_time: float):
        self.logger.info("Начало движения вперёд...")
        self.control_wheel(Wheel.LEFT, WheelState.FORWARD)
        self.control_wheel(Wheel.RIGHT, WheelState.FORWARD)
        time.sleep(move_time)
        self.stop()
        self.logger.success("Движение вперёд завершено")
    
    def stop(self):
        self.logger.info("Остановка двигателя...")
        self.control_wheel(Wheel.LEFT, WheelState.STOP)
        self.control_wheel(Wheel.RIGHT, WheelState.STOP)
        self.logger.success("Двигатель остановлен")

    def turn_left(self):
        self.logger.info("Поворот налево...")
        self.control_wheel(Wheel.LEFT, WheelState.REVERSE)
        self.control_wheel(Wheel.RIGHT, WheelState.FORWARD)


    def turn_right(self):
        self.logger.info("Поворот направо...")
        self.control_wheel(Wheel.LEFT, WheelState.FORWARD)
        self.control_wheel(Wheel.RIGHT, WheelState.REVERSE)


engine = Engine()
engine.forward(move_time=1)