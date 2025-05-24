import cv2
from system.camera import CameraProcessor

def run_camera_processing():
    processor = CameraProcessor(debug=True, process_frame_width=640)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: Не удалось открыть веб-камеру.")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Ошибка: Не удалось получить кадр с веб-камеры.")
                break

            results = processor.get_processing_results(frame)

            distance_px = results.get("distance_px")
            angle_deg = results.get("angle_to_target_deg")

            dist_str = f"{distance_px:.1f} px" if distance_px is not None else "N/A"
            angle_str = f"{angle_deg:.1f} deg" if angle_deg is not None else "N/A"
            
            print(f"Расстояние до цели: {dist_str}, Угол до цели: {angle_str}")

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    finally:
        cap.release()
        if processor.debug_mode:
            final_hsv = processor.get_current_hsv_ranges()
            print("\nИтоговые HSV диапазоны (если debug=True):")
            for color_name, values in final_hsv.items():
                print(f'    "{color_name}": [{values[0]}, {values[1]}, {values[2]}, {values[3]}, {values[4]}, {values[5]}],')
            
            processor.release_windows()

        cv2.destroyAllWindows()
        print("Веб-камера освобождена, окна закрыты.")

if __name__ == "__main__":
    run_camera_processing()