"""Debug-Overlay"""
import cv2

class Overlay:
    def __init__(self, config):
        self.config = config
        self.show_debug = config.get('gui.show_debug_info', True)
        self.show_landmarks = config.get('gui.show_landmarks', True)
        self.show_controls = config.get('gui.show_controls_hint', True)
    
    def draw_tracking_info(self, frame, delta_x, delta_y, mouth_opening, is_calibrated):
        if not self.show_debug:
            return
        
        text_color = tuple(self.config.get('colors.text', [255, 255, 255]))
        status_color = tuple(self.config.get('colors.calibrated' if is_calibrated else 'colors.error', [0, 255, 0]))
        
        status_text = "Status: AKTIV" if is_calibrated else "Status: KALIBRIERUNG"
        cv2.putText(frame, status_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, f"Delta X: {delta_x:.3f} Y: {delta_y:.3f}", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        cv2.putText(frame, f"Mouth: {mouth_opening:.3f}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
    
    def draw_click_indicator(self, frame):
        h, w = frame.shape[:2]
        click_color = tuple(self.config.get('colors.click_indicator', [0, 0, 255]))
        cv2.putText(frame, "ACTION!", (w - 150, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, click_color, 2)
    
    def draw_controls(self, frame):
        if not self.show_controls:
            return
        h, w = frame.shape[:2]
        text_color = tuple(self.config.get('colors.text', [255, 255, 255]))
        cv2.putText(frame, "ESC: Beenden", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
