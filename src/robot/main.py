import time
import signal
from engine import Engine
from broker import CommandReciever
from common.command import Command as CommonCommand

# --- Конфигурация ---
MQTT_BROKER_HOST = "192.168.1.101"
MQTT_BROKER_PORT = 1883
MQTT_COMMAND_TOPIC = "robot/command"
# --------------------

robot_engine = Engine()
command_receiver = CommandReciever(host=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)

keep_running = True

ROBOT_ACTION_DURATION = 0.25

def signal_handler(sig, frame):
    global keep_running
    robot_engine.logger.warning(f"Получен сигнал {sig}, завершение работы робота...")
    keep_running = False

def mqtt_commands_callback(command_str: str):
    robot_engine.logger.info(f"MQTT | Получена команда: '{command_str}'")
    try:
        cmd_enum = CommonCommand(command_str)
        
        if cmd_enum == CommonCommand.MOVE_FORWARD:
            robot_engine.forward()
        elif cmd_enum == CommonCommand.TURN_LEFT:
            robot_engine.turn_left()
        elif cmd_enum == CommonCommand.TURN_RIGHT:
            robot_engine.turn_right()
        elif cmd_enum == CommonCommand.STOP:
            robot_engine.stop()
    except ValueError:
        robot_engine.logger.error(f"MQTT | Неизвестная команда: '{command_str}'")
    except Exception as e:
        robot_engine.logger.error(f"MQTT | Ошибка при обработке команды '{command_str}': {e}")

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    robot_engine.logger.info("Запуск контроллера робота...")

    if not command_receiver.connect(commands_callback=mqtt_commands_callback):
        robot_engine.logger.critical("Не удалось подключиться к MQTT брокеру. Выход.")
        robot_engine.cleanup()
        exit(1)
    
    robot_engine.logger.info(f"Робот слушает команды на MQTT {MQTT_BROKER_HOST}")

    try:
        while keep_running:
            if not command_receiver.connected:
                robot_engine.logger.error("MQTT соединение потеряно. Попытка переподключения...")
                if not command_receiver.connect(commands_callback=mqtt_commands_callback):
                    robot_engine.logger.critical("Не удалось переподключиться к MQTT. Выход.")
                    break 
                else:
                    robot_engine.logger.info("Успешно переподключено к MQTT.")
            time.sleep(0.1)
    except Exception as e:
        robot_engine.logger.critical(f"Критическая ошибка в главном цикле робота: {e}", exc_info=True)
    finally:
        robot_engine.logger.info("Завершение работы контроллера робота...")
        if command_receiver.connected:
            command_receiver.disconnect()
        robot_engine.stop()
        robot_engine.cleanup()
        robot_engine.logger.info("Контроллер робота остановлен.")


if __name__ == "__main__":
    main()
