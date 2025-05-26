# main.py
import cv2
from system.camera import CameraProcessor
from system.control import RobotNavigationFSM # Убедитесь, что импортируется обновленный FSM
from system.broker import CommandSender
from common.command import Command
import time

def run_camera_processing():
    # FSM Configuration Parameters
    FSM_ANGLE_TOLERANCE_DEG = 25.0  # Градусы для ПЕРВИЧНОЙ (грубой) ориентации
    FSM_STRAIGHT_MOVE_ANGLE_THRESHOLD_DEG = 30.0 # Градусы для движения прямо (-15...+15)
    FSM_DISTANCE_TOLERANCE_PX = 50.0 # Пиксели, чтобы считать цель "достигнутой"
    FSM_TURN_SPEED = 0.5             # Условная скорость поворота (для RobotAction)
    FSM_MOVE_SPEED = 1.0             # Условная скорость движения (для RobotAction)
    
    # Интервал отправки команд роботу в секундах
    COMMAND_SEND_INTERVAL_S = 2.0  # Например, 3 секунды

    processor = CameraProcessor(debug=True, process_frame_width=640)
    # Укажите правильный IP вашего MQTT брокера
    broker = CommandSender(host="192.168.1.101", port=1883) # TODO: Верунть 192.168.1.101
    
    fsm = RobotNavigationFSM(
        angle_tolerance=FSM_ANGLE_TOLERANCE_DEG,
        distance_tolerance=FSM_DISTANCE_TOLERANCE_PX,
        turn_speed=FSM_TURN_SPEED,
        move_speed=FSM_MOVE_SPEED,
        straight_angle_threshold=FSM_STRAIGHT_MOVE_ANGLE_THRESHOLD_DEG # Передаем новый параметр
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: Не удалось открыть веб-камеру.")
        return

    if not broker.connect():
        print("Ошибка: Не удалось подключиться к MQTT брокеру.")
        cap.release()
        cv2.destroyAllWindows()
        return

    target_is_known = False
    last_command_send_time = 0.0  # Время последней ОТПРАВКИ команды брокеру
    # Храним последнюю команду, ФАКТИЧЕСКИ отправленную роботу, чтобы не дублировать
    last_actually_sent_command_to_robot: Command | None = None


    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Ошибка: Не удалось получить кадр с веб-камеры.")
                break

            results = processor.get_processing_results(frame)
            distance_px = results.get("distance_px")
            angle_deg = results.get("angle_to_target_deg")

            robot_action_fsm: RobotAction | None = None # Действие, которое FSM считает нужным СЕЙЧАС

            if distance_px is not None and angle_deg is not None: # Цель видна
                if not target_is_known:
                    fsm.set_target(angle_deg, distance_px)
                    target_is_known = True
                robot_action_fsm = fsm.update(angle_deg, distance_px)
            else: # Цель не видна
                if target_is_known:
                    fsm.clear_target() # FSM перейдет в IDLE
                    target_is_known = False
                # Даже если цели нет, FSM должен выдать действие (например, "idle")
                robot_action_fsm = fsm.update(0.0, 0.0) # FSM обработает отсутствие цели

            # Преобразуем RobotAction от FSM в common.command.Command для отправки
            current_desired_command_for_robot: Command | None = None
            if robot_action_fsm:
                action_cmd_str = robot_action_fsm.command
                if action_cmd_str == "idle":
                    current_desired_command_for_robot = Command.STOP 
                elif action_cmd_str == "turn_right":
                    current_desired_command_for_robot = Command.TURN_RIGHT
                elif action_cmd_str == "turn_left":
                    current_desired_command_for_robot = Command.TURN_LEFT
                elif action_cmd_str == "move_forward":
                    current_desired_command_for_robot = Command.MOVE_FORWARD
                elif action_cmd_str == "stop": # Если FSM явно сказал "stop" (например, цель достигнута)
                    current_desired_command_for_robot = Command.STOP
            
            # Логика принятия решения об отправке команды
            current_time = time.time()
            should_send_mqtt_command_now = False
            
            if current_desired_command_for_robot:
                # 1. Срочная отправка STOP: если FSM хочет STOP, а последняя отправленная команда была НЕ STOP.
                is_urgent_stop_request = (current_desired_command_for_robot == Command.STOP and \
                                          last_actually_sent_command_to_robot != Command.STOP)

                # 2. Плановая отправка: если прошел интервал И (команда изменилась ИЛИ это не STOP).
                #    Не отправляем STOP повторно по интервалу, если робот уже получил STOP.
                #    Отправляем другие команды по интервалу, даже если они не изменились (для "подтверждения" роботу)
                #    ИЛИ если команда изменилась.
                time_since_last_send = current_time - last_command_send_time
                interval_elapsed = (time_since_last_send >= COMMAND_SEND_INTERVAL_S)

                command_changed = (current_desired_command_for_robot != last_actually_sent_command_to_robot)

                if is_urgent_stop_request:
                    should_send_mqtt_command_now = True
                elif interval_elapsed:
                    if command_changed: # Если команда изменилась, точно отправляем
                        should_send_mqtt_command_now = True
                    # Если команда не изменилась, но это команда движения - можно "подтвердить"
                    # (Это поведение можно настроить: нужно ли подтверждать одну и ту же команду движения)
                    # Сейчас: отправляем, если команда изменилась ИЛИ (это не STOP и не IDLE -> т.е. движение/поворот)
                    elif current_desired_command_for_robot != Command.STOP: # Повторная отправка команд движения
                         should_send_mqtt_command_now = True
            
            actual_mqtt_payload_sent_str = "No MQTT Cmd This Frame"

            if should_send_mqtt_command_now and current_desired_command_for_robot:
                if broker.send(current_desired_command_for_robot):
                    last_command_send_time = current_time
                    last_actually_sent_command_to_robot = current_desired_command_for_robot
                    actual_mqtt_payload_sent_str = current_desired_command_for_robot.value
                else:
                    actual_mqtt_payload_sent_str = "MQTT Send FAIL"
            elif current_desired_command_for_robot: # Команда есть, но не отправляем (из-за интервала/логики)
                 actual_mqtt_payload_sent_str = f"Throttled ({current_desired_command_for_robot.value})"
                
            # Отладочный вывод
            dist_str = f"{distance_px:.1f} px" if distance_px is not None else "N/A"
            angle_str = f"{angle_deg:.1f} deg" if angle_deg is not None else "N/A"
            fsm_action_str = robot_action_fsm.command if robot_action_fsm else "N/A"
            
            print(f"Dist: {dist_str}, Angle: {angle_str}, FSM State: {fsm.get_current_state_name()}, "
                  f"FSM Action: {fsm_action_str}, Desired MQTT: {current_desired_command_for_robot.value if current_desired_command_for_robot else 'None'}, "
                  f"SentToMQTT: {actual_mqtt_payload_sent_str}, LastSentToRobot: {last_actually_sent_command_to_robot.value if last_actually_sent_command_to_robot else 'None'}")

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    finally:
        print("Exiting program...")
        if broker.connected: # Отправляем STOP только если были подключены
            print("Sending final STOP command to robot...")
            broker.send(Command.STOP) 
            broker.disconnect()
        
        cap.release()
        if processor.debug_mode: # Предполагается, что у CameraProcessor есть такой атрибут
            # Этот код был в вашем оригинальном main.py, оставляю его
            final_hsv = processor.get_current_hsv_ranges()
            print("\nИтоговые HSV диапазоны (если debug=True):")
            for color_name, values in final_hsv.items():
                print(f'    "{color_name}": [{values[0]}, {values[1]}, {values[2]}, {values[3]}, {values[4]}, {values[5]}],')
            processor.release_windows() # Предполагается, что есть такой метод

        cv2.destroyAllWindows()
        print("Веб-камера освобождена, MQTT отключен, окна закрыты.")

if __name__ == "__main__":
    run_camera_processing()