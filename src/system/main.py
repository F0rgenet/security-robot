import cv2
from system.camera import CameraProcessor
from system.control import RobotNavigationFSM
from system.broker import CommandSender
from common.command import Command

def run_camera_processing():
    # FSM Configuration Parameters
    FSM_ANGLE_TOLERANCE_DEG = 10.0  # Degrees for orientation
    FSM_DISTANCE_TOLERANCE_PX = 50.0 # Pixels to consider target "reached"
    FSM_TURN_SPEED = 0.5             # Abstract speed unit for FSM logic
    FSM_MOVE_SPEED = 1.0             # Abstract speed unit for FSM logic
    FSM_ANGLE_TOLERANCE_WHILE_MOVING_DEG = 15.0 # Wider tolerance while moving

    processor = CameraProcessor(debug=True, process_frame_width=640)
    broker = CommandSender(host="192.168.1.104", port=1883)
    fsm = RobotNavigationFSM(
        angle_tolerance=FSM_ANGLE_TOLERANCE_DEG,
        distance_tolerance=FSM_DISTANCE_TOLERANCE_PX,
        turn_speed=FSM_TURN_SPEED,
        move_speed=FSM_MOVE_SPEED,
        angle_tolerance_while_moving=FSM_ANGLE_TOLERANCE_WHILE_MOVING_DEG
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

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Ошибка: Не удалось получить кадр с веб-камеры.")
                break

            results = processor.get_processing_results(frame)
            distance_px = results.get("distance_px")
            angle_deg = results.get("angle_to_target_deg")

            robot_action = None

            if distance_px is not None and angle_deg is not None:
                if not target_is_known:
                    fsm.set_target(angle_deg, distance_px)
                    target_is_known = True
                robot_action = fsm.update(angle_deg, distance_px)
            else:
                if target_is_known:
                    fsm.clear_target()
                    target_is_known = False
                robot_action = fsm.update(0.0, 0.0)

            command_to_send = None
            if robot_action:
                action_cmd_str = robot_action.command
                if action_cmd_str == "idle":
                    command_to_send = Command.STOP 
                elif action_cmd_str == "turn_right":
                    command_to_send = Command.TURN_RIGHT
                elif action_cmd_str == "turn_left":
                    command_to_send = Command.TURN_LEFT
                elif action_cmd_str == "move_forward":
                    command_to_send = Command.MOVE_FORWARD
                elif action_cmd_str == "stop":
                    command_to_send = Command.STOP
            
            if command_to_send:
                broker.send(command_to_send)
            
            dist_str = f"{distance_px:.1f} px" if distance_px is not None else "N/A"
            angle_str = f"{angle_deg:.1f} deg" if angle_deg is not None else "N/A"
            action_str = robot_action.command if robot_action else "N/A"
            
            print(f"Dist: {dist_str}, Angle: {angle_str}, FSM State: {fsm.get_current_state_name()}, Action: {action_str}, Sent: {command_to_send.value if command_to_send else 'None'}")

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    finally:
        broker.send(Command.STOP)
        broker.disconnect()
        cap.release()
        if processor.debug_mode:
            final_hsv = processor.get_current_hsv_ranges()
            print("\nИтоговые HSV диапазоны (если debug=True):")
            for color_name, values in final_hsv.items():
                print(f'    "{color_name}": [{values[0]}, {values[1]}, {values[2]}, {values[3]}, {values[4]}, {values[5]}],')
            
            processor.release_windows()

        cv2.destroyAllWindows()
        print("Веб-камера освобождена, MQTT отключен, окна закрыты.")

if __name__ == "__main__":
    run_camera_processing()