from typing import Callable
import paho.mqtt.client as mqtt
from common.logged import LoggedClass

class CommandReciever(LoggedClass):
    DEFAULT_MQTT_HOST = "localhost"
    DEFAULT_MQTT_PORT = 1883
    DEFAULT_COMMAND_TOPIC = "robot/command"
    DEFAULT_CLIENT_ID = "robot_receiver"

    def __init__(self, 
                 host: str = DEFAULT_MQTT_HOST, 
                 port: int = DEFAULT_MQTT_PORT,
                 client_id: str = DEFAULT_CLIENT_ID,
                 command_topic: str = DEFAULT_COMMAND_TOPIC):
        super().__init__() # Если LoggedClass используется
        self.host = host
        self.port = port
        self.client_id = client_id
        self.command_topic = command_topic
        
        # Перемещаем создание клиента сюда, чтобы client_id применялся сразу
        self.client = mqtt.Client(client_id=self.client_id)
        self.logger.info(f"Инициализация CommandReciever для {self.host}:{self.port}, client_id: {self.client_id}")
        self.connected = False
        self._commands_callback_ref: Callable | None = None # Храним ссылку на callback

    def connect(self, commands_callback: Callable) -> bool | None:
        self.logger.info("Подключение к MQTT...")
        try:
            self.client.connect("192.168.1.101")
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
