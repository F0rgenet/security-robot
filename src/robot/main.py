# robot_controller.py (или как вы его назовете)
import time
import signal
from engine import Engine # Убедитесь, что путь правильный
from broker import CommandReciever # Ваш класс для приема MQTT команд
from common.command import Command as CommonCommand # Enum команд

# --- Конфигурация ---
MQTT_BROKER_HOST = "192.168.1.101" # IP вашего MQTT брокера
MQTT_BROKER_PORT = 1883
MQTT_COMMAND_TOPIC = "robot/command"
# --------------------

robot_engine = Engine()
command_receiver = CommandReciever(host=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT) # Передаем хост/порт если нужно

keep_running = True

# Длительность действия команды на роботе (можно сделать глобальной константой)
ROBOT_ACTION_DURATION = 0.7 # секунды (должно совпадать с DEFAULT_ACTION_DURATION_S в Engine или передаваться)

def handle_command(command_str: str):
    global robot_engine # Если robot_engine - глобальная переменная
    try:
        command_enum_val = Command(command_str) # Преобразуем строку в ваш Enum Command

        robot_engine.logger.info(f"Получена команда для движка: {command_enum_val.value}")

        # Теперь мы просто вызываем метод. Engine сам позаботится о длительности.
        if command_enum_val == Command.MOVE_FORWARD:
            robot_engine.forward(duration=ROBOT_ACTION_DURATION)
        elif command_enum_val == Command.TURN_LEFT:
            robot_engine.turn_left(duration=ROBOT_ACTION_DURATION)
        elif command_enum_val == Command.TURN_RIGHT:
            robot_engine.turn_right(duration=ROBOT_ACTION_DURATION)
        elif command_enum_val == Command.STOP:
            robot_engine.stop() # Команда STOP отменяет все и останавливает
        else:
            robot_engine.logger.warning(f"Неизвестная или необработанная команда Enum: {command_enum_val}")

    except ValueError:
        robot_engine.logger.error(f"Не удалось распознать строку команды: {command_str}")
    except Exception as e:
        robot_engine.logger.error(f"Ошибка при выполнении команды {command_str}: {e}")

def signal_handler(sig, frame):
    global keep_running
    robot_engine.logger.warning(f"Получен сигнал {sig}, завершение работы робота...")
    keep_running = False

def mqtt_commands_callback(command_str: str):
    robot_engine.logger.info(f"MQTT | Получена команда: '{command_str}'")
    try:
        cmd_enum = CommonCommand(command_str) # Преобразуем строку в Enum из common.command
        
        if cmd_enum == CommonCommand.MOVE_FORWARD:
            robot_engine.forward() # Используем длительность и скорость по умолчанию из Engine
        elif cmd_enum == CommonCommand.TURN_LEFT:
            robot_engine.turn_left()
        elif cmd_enum == CommonCommand.TURN_RIGHT:
            robot_engine.turn_right()
        elif cmd_enum == CommonCommand.STOP:
            robot_engine.stop()
        # Добавьте обработку других команд, если они есть
    except ValueError:
        robot_engine.logger.error(f"MQTT | Неизвестная команда: '{command_str}'")
    except Exception as e:
        robot_engine.logger.error(f"MQTT | Ошибка при обработке команды '{command_str}': {e}")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    robot_engine.logger.info("Запуск контроллера робота...")

    # Передаем callback в CommandReciever. Убедитесь, что ваш CommandReciever
    # имеет метод connect, принимающий callback, и client_id.
    # В вашем первом broker.py был client_id="robot" жестко задан.
    if not command_receiver.connect(commands_callback=mqtt_commands_callback):
        robot_engine.logger.critical("Не удалось подключиться к MQTT брокеру. Выход.")
        robot_engine.cleanup()
        exit(1)
    
    robot_engine.logger.info(f"Робот слушает команды на MQTT {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}, топик: {command_receiver.client.SUBSCRIBE_TOPIC if hasattr(command_receiver.client, 'SUBSCRIBE_TOPIC') else MQTT_COMMAND_TOPIC}") # Адаптируйте топик если нужно

    try:
        while keep_running:
            # Здесь можно добавить логику для робота, не связанную с MQTT, если нужно.
            # Например, чтение сенсоров, проверка заряда батареи и т.д.
            # Сейчас основной цикл просто ждет, пока MQTT и таймеры делают свою работу.
            if not command_receiver.connected: # Проверка, если соединение разорвалось
                robot_engine.logger.error("MQTT соединение потеряно. Попытка переподключения...")
                # Добавьте логику переподключения если нужно, или просто выходите
                # Для простоты, пока выходим.
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
            # Отправка последней команды STOP роботу не нужна здесь,
            # т.к. main.py на управляющем ПК это сделает.
            # Робот сам остановится по таймеру или уже стоит.
            command_receiver.disconnect()
        robot_engine.stop() # Гарантированная остановка моторов
        robot_engine.cleanup() # Очистка GPIO
        robot_engine.logger.info("Контроллер робота остановлен.")