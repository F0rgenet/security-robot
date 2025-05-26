# src/robot/engine.py

from common.logged import LoggedClass
import RPi.GPIO as GPIO
import time
import threading
from enum import Enum

class WheelState(Enum):
    FORWARD = "forward"
    REVERSE = "reverse"
    STOP = "stop"

class Wheel(Enum):
    LEFT = "left"
    RIGHT = "right"

class Engine(LoggedClass):
    DEFAULT_ACTION_DURATION_S = 0.25

    def __init__(self):
        super().__init__()
        self.logger.info("Инициализация двигателя (с авто-остановкой)")
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

        self._current_action_timer = None # Для хранения ссылки на активный таймер

    def _cancel_previous_action_timer(self):
        """Отменяет предыдущий активный таймер авто-остановки, если он есть."""
        if self._current_action_timer and self._current_action_timer.is_alive():
            self._current_action_timer.cancel()
            # self.logger.debug("Previous action timer cancelled.")
        self._current_action_timer = None

    def _start_action_timer(self, duration: float):
        """Запускает таймер, который вызовет _auto_stop через 'duration' секунд."""
        self._cancel_previous_action_timer() # Отменяем старый таймер перед запуском нового
        self._current_action_timer = threading.Timer(duration, self._auto_stop)
        self._current_action_timer.start()

    def _auto_stop(self):
        """Метод, вызываемый таймером для автоматической остановки моторов."""
        self.logger.info(f"Авто-остановка после {self.DEFAULT_ACTION_DURATION_S} сек.")
        self.control_wheel(Wheel.LEFT, WheelState.STOP)
        self.control_wheel(Wheel.RIGHT, WheelState.STOP)
        self._current_action_timer = None # Сбрасываем таймер

    def control_wheel(self, wheel: Wheel, wheel_state: WheelState):
        # self.logger.debug(f"Control wheel {wheel.value}: {wheel_state.value}") # Для отладки
        pins = (self.IN1, self.IN2) if wheel == Wheel.LEFT else (self.IN4, self.IN3)
        if wheel_state == WheelState.FORWARD:
            GPIO.output(pins[0], GPIO.HIGH)
            GPIO.output(pins[1], GPIO.LOW)
        elif wheel_state == WheelState.REVERSE:
            GPIO.output(pins[0], GPIO.LOW)
            GPIO.output(pins[1], GPIO.HIGH)
        else: # WheelState.STOP
            GPIO.output(pins[0], GPIO.LOW)
            GPIO.output(pins[1], GPIO.LOW)

    def forward(self, duration: float = DEFAULT_ACTION_DURATION_S):
        self.logger.info(f"Начало движения вперёд (на {duration} сек)...")
        self.control_wheel(Wheel.LEFT, WheelState.REVERSE)
        self.control_wheel(Wheel.RIGHT, WheelState.REVERSE)
        self._start_action_timer(duration)
    
    def stop(self):
        """
        Принудительная остановка по команде от управляющего ПК.
        Отменяет любой таймер и останавливает моторы.
        """
        self.logger.info("Команда STOP: Остановка двигателя...")
        self._cancel_previous_action_timer() # Важно отменить таймер
        self.control_wheel(Wheel.LEFT, WheelState.STOP)
        self.control_wheel(Wheel.RIGHT, WheelState.STOP)
        self.logger.success("Двигатель остановлен по команде STOP")

    def turn_left(self, duration: float = DEFAULT_ACTION_DURATION_S):
        self.logger.info(f"Поворот налево (на {duration} сек)...")
        self.control_wheel(Wheel.LEFT, WheelState.REVERSE)
        self.control_wheel(Wheel.RIGHT, WheelState.FORWARD)
        self._start_action_timer(duration)

    def turn_right(self, duration: float = DEFAULT_ACTION_DURATION_S):
        self.logger.info(f"Поворот направо (на {duration} сек)...")
        self.control_wheel(Wheel.LEFT, WheelState.FORWARD)
        self.control_wheel(Wheel.RIGHT, WheelState.REVERSE)
        self._start_action_timer(duration)

    def cleanup(self):
        """Метод для очистки GPIO при завершении работы."""
        self.logger.info("Очистка GPIO...")
        self.stop() # Убедимся, что моторы остановлены и таймеры отменены
        GPIO.cleanup()
        self.logger.success("GPIO очищен.")