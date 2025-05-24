from enum import Enum
import paho.mqtt.client as mqtt
from common.logged import LoggedClass
from common.command import Command

class CommandSender(LoggedClass):
    COMMAND_TOPIC = "robot/command"

    def __init__(self, host: str = "localhost", port: int = 1883, client_id_pub: str = "robot_pub"):
        super().__init__()
        self.pub_client = mqtt.Client(client_id=client_id_pub)
        self.host = host
        self.port = port
        self.connected = False

    def connect(self) -> bool:
        try:
            self.pub_client.connect(self.host, self.port)
            self.pub_client.loop_start()

            self.connected = True
            self.logger.success(f"MQTT connected: {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"MQTT connection error: {e}")
            return False

    def disconnect(self) -> None:
        """
        Stop loops and disconnect both clients.
        """
        if self.connected:
            self.pub_client.loop_stop()
            self.pub_client.disconnect()
            self.connected = False
            self.logger.success("MQTT disconnected")

    def send(self, command: Command) -> bool:
        if not self.connected:
            self.logger.warning("Send called before MQTT connect")
            return False
        payload = command.value
        result = self.pub_client.publish(self.COMMAND_TOPIC, payload)
        print(result)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(f"Sent command: {payload}")
            return True
        else:
            self.logger.error(f"Failed to send: {payload}")
            return False

    def _make_handler(self, callback):
        def handler(client, userdata, msg):
            raw = msg.payload.decode()
            self.logger.info(f"Received raw: {raw}")
            try:
                cmd = Command(raw)
                self.logger.info(f"Parsed command: {cmd}")
                callback(cmd)
            except ValueError:
                self.logger.warning(f"Unknown command: {raw}")
        return handler