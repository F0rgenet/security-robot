import cv2
import numpy as np
import math

class CameraProcessor:
    DEFAULT_HSV_RANGES = {
        "green": [40, 40, 40, 95, 255, 255],
        "pink": [140, 60, 80, 175, 255, 255],
        "blue": [95, 80, 80, 128, 255, 255],
    }

    OUTPUT_WINDOW_NAME = "Camera Debug Output"

    KERNEL_MORPH_OPEN = np.ones((5, 5), np.uint8)
    KERNEL_MORPH_CLOSE_5x5 = np.ones((5, 5), np.uint8)
    KERNEL_MORPH_CLOSE_7x7 = np.ones((7, 7), np.uint8)

    def __init__(self, process_frame_width=640, debug=False, initial_hsv_ranges=None):
        self.process_frame_width = process_frame_width
        self.debug_mode = debug
        
        if initial_hsv_ranges is None:
            self.hsv_ranges = {k: list(v) for k, v in self.DEFAULT_HSV_RANGES.items()}
        else:
            self.hsv_ranges = {k: list(v) for k, v in initial_hsv_ranges.items()}

        if self.debug_mode:
            self._setup_debug_windows()

    def _setup_debug_windows(self):
        cv2.startWindowThread()
        cv2.namedWindow(self.OUTPUT_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.OUTPUT_WINDOW_NAME, 960, 720)

    def _find_largest_contour_and_centroid(self, mask, min_area=30):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None

        largest_contour = None
        max_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area > min_area and area > max_area:
                max_area = area
                largest_contour = c
        
        if largest_contour is None:
            return None, None
            
        M = cv2.moments(largest_contour)
        if M["m00"] == 0:
            return None, None
        
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy), largest_contour

    def get_processing_results(self, original_img, base_min_area_scale_factor=1.0):
        scale_ratio = 1.0
        if self.process_frame_width and original_img.shape[1] > self.process_frame_width:
            scale_ratio = self.process_frame_width / original_img.shape[1]
            height = int(original_img.shape[0] * scale_ratio)
            processed_img = cv2.resize(original_img, (self.process_frame_width, height), interpolation=cv2.INTER_AREA)
        else:
            processed_img = original_img.copy()

        current_min_area_scale = (scale_ratio ** 2) * base_min_area_scale_factor
        
        output_img = processed_img.copy() if self.debug_mode else None
        hsv_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2HSV)

        current_hsv_cv = {}
        for color, values in self.hsv_ranges.items():
            current_hsv_cv[color] = (np.array(values[0:3]), np.array(values[3:6]))

        min_area_pink_blue = int(50 * current_min_area_scale)
        min_area_green = int(100 * current_min_area_scale)

        lower_pink, upper_pink = current_hsv_cv["pink"]
        mask_pink = cv2.inRange(hsv_img, lower_pink, upper_pink)
        mask_pink = cv2.morphologyEx(mask_pink, cv2.MORPH_OPEN, self.KERNEL_MORPH_OPEN)
        mask_pink = cv2.morphologyEx(mask_pink, cv2.MORPH_CLOSE, self.KERNEL_MORPH_CLOSE_5x5)
        centroid_pink, _ = self._find_largest_contour_and_centroid(mask_pink, min_area=min_area_pink_blue)

        lower_blue, upper_blue = current_hsv_cv["blue"]
        mask_blue = cv2.inRange(hsv_img, lower_blue, upper_blue)
        mask_blue = cv2.morphologyEx(mask_blue, cv2.MORPH_OPEN, self.KERNEL_MORPH_OPEN)
        mask_blue = cv2.morphologyEx(mask_blue, cv2.MORPH_CLOSE, self.KERNEL_MORPH_CLOSE_5x5)
        centroid_blue, _ = self._find_largest_contour_and_centroid(mask_blue, min_area=min_area_pink_blue)

        robot_center = None
        robot_heading_rad = None
        distance_to_target = None
        angle_to_target_deg = None

        if centroid_pink and self.debug_mode and output_img is not None:
            cv2.circle(output_img, centroid_pink, 5, (203, 192, 255), -1)
        if centroid_blue and self.debug_mode and output_img is not None:
            cv2.circle(output_img, centroid_blue, 5, (255, 192, 203), -1)

        if centroid_pink and centroid_blue:
            if self.debug_mode and output_img is not None:
                cv2.line(output_img, centroid_pink, centroid_blue, (255, 0, 255), 2)
            
            robot_center_x = (centroid_pink[0] + centroid_blue[0]) // 2
            robot_center_y = (centroid_pink[1] + centroid_blue[1]) // 2
            robot_center = (robot_center_x, robot_center_y)
            if self.debug_mode and output_img is not None:
                cv2.circle(output_img, robot_center, 5, (255, 255, 0), -1)

            robot_dx = centroid_pink[0] - centroid_blue[0] 
            robot_dy = centroid_pink[1] - centroid_blue[1] 
            robot_heading_rad = math.atan2(-robot_dy, robot_dx)

        lower_green, upper_green = current_hsv_cv["green"]
        mask_green = cv2.inRange(hsv_img, lower_green, upper_green)
        mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, self.KERNEL_MORPH_OPEN)
        mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, self.KERNEL_MORPH_CLOSE_7x7)
        centroid_green, _ = self._find_largest_contour_and_centroid(mask_green, min_area=min_area_green)
        
        if centroid_green and self.debug_mode and output_img is not None:
            cv2.circle(output_img, centroid_green, 5, (0, 255, 0), -1)

        if robot_center and centroid_green:
            if self.debug_mode and output_img is not None:
                cv2.line(output_img, robot_center, centroid_green, (0, 255, 255), 2)

            distance_to_target = math.hypot(centroid_green[0] - robot_center[0], centroid_green[1] - robot_center[1])
            
            target_dx = centroid_green[0] - robot_center[0]
            target_dy = centroid_green[1] - robot_center[1]
            world_angle_to_target_rad = math.atan2(-target_dy, target_dx)
            
            if robot_heading_rad is not None:
                steer_angle_rad = world_angle_to_target_rad - robot_heading_rad
                steer_angle_rad = (steer_angle_rad + math.pi) % (2 * math.pi) - math.pi
                angle_to_target_deg = math.degrees(steer_angle_rad)
            else:
                angle_to_target_deg = math.degrees(world_angle_to_target_rad)

            if self.debug_mode and output_img is not None:
                mid_line_x = (robot_center[0] + centroid_green[0]) // 2
                mid_line_y = (robot_center[1] + centroid_green[1]) // 2
                
                dist_text = f"Dist: {distance_to_target:.0f}px"
                angle_text = f"Angle: {angle_to_target_deg:.0f}deg"

                font_scale = 0.5
                thickness = 1
                cv2.putText(output_img, dist_text, (mid_line_x + 5, mid_line_y - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0,0,0), thickness + 1, cv2.LINE_AA)
                cv2.putText(output_img, dist_text, (mid_line_x + 5, mid_line_y - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
                
                cv2.putText(output_img, angle_text, (mid_line_x + 5, mid_line_y + 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0,0,0), thickness + 1, cv2.LINE_AA)
                cv2.putText(output_img, angle_text, (mid_line_x + 5, mid_line_y + 15), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

        if self.debug_mode and output_img is not None:
            cv2.imshow(self.OUTPUT_WINDOW_NAME, output_img)

        results = {
            "robot_center_uv": robot_center,
            "robot_heading_rad": robot_heading_rad,
            "target_center_uv": centroid_green,
            "distance_px": distance_to_target,
            "angle_to_target_deg": angle_to_target_deg,
            "scale_ratio": scale_ratio
        }
        return results

    def get_current_hsv_ranges(self):
        return self.hsv_ranges

    def release_windows(self):
        if self.debug_mode:
            if cv2.getWindowProperty(self.OUTPUT_WINDOW_NAME, cv2.WND_PROP_VISIBLE) >= 1:
                cv2.destroyWindow(self.OUTPUT_WINDOW_NAME)
