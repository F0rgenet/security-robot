from typing import Callable
import paho.mqtt.client as mqtt
from common.logged import LoggedClass

class CommandReciever(LoggedClass):
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client(client_id="robot")
        self.logger.info("Инициализация командного брокера")
        self.connected = False

    def connect(self, commands_callback: Callable) -> bool | None:
        self.logger.info("Подключение к MQTT...")
        try:
            self.client.connect("localhost")
            self.client.subscribe("robot/command")
            self.client.on_message = self.commands_callback_builder(commands_callback)
            self.client.loop_start()
            self.connected = True
            self.logger.success("Подключение к MQTT успешно")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при подключении к MQTT: {e}")
            return False
    
    def disconnect(self):
        self.logger.info("Отключение от MQTT...")
        self.client.disconnect()
        self.connected = False
        self.logger.success("Отключение от MQTT успешно")

    def commands_callback_builder(self, commands_callback: Callable):
        def on_message(client, userdata, message):
            # TODO: Работать с payload
            self.logger.info(f"Получено сообщение: {message.payload.decode()}")
            command = message.payload.decode()
            self.logger.info(f"Команда: {command}")
            commands_callback(command)
        return on_message
