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
        for pin in (self.IN1, self.IN2, self.IN3, self.IN4, self.ENA, self.ENB):
            GPIO.setup(pin, GPIO.OUT)

        GPIO.output(self.ENA, GPIO.HIGH)
        GPIO.output(self.ENB, GPIO.HIGH)
    
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
        

    def forward(self):
        self.logger.info("Начало движения вперёд...")
        self.control_wheel(Wheel.LEFT, WheelState.FORWARD)
        self.control_wheel(Wheel.RIGHT, WheelState.FORWARD)
    
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
