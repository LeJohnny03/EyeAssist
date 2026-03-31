"""Erweitertes Debug-Overlay für EyeAssist"""
import cv2

class Overlay:
    def __init__(self, config):
        self.config          = config
        self.show_debug      = config.get('gui.show_debug_info', True)
        self.show_landmarks  = config.get('gui.show_landmarks', True)
        self.show_controls   = config.get('gui.show_controls_hint', True)
        
        # Target-Tracking-Status (für TTT-Metrik)
        self._target_active = False
        self._target_x      = 0
        self._target_y      = 0
        self._target_radius = 30


    def spawn_target(self, frame_w: int, frame_h: int, margin: int = 60) -> tuple[int, int]:
        """Spawnt ein Ziel an zufälliger Position. Gibt (x, y) zurück."""
        import random
        self._target_x = random.randint(margin, frame_w - margin)
        self._target_y = random.randint(margin, frame_h - margin)
        self._target_active = True
        return self._target_x, self._target_y

    def dismiss_target(self) -> None:
        """Blendet das aktive Ziel aus (nach erfolgreichem Klick)."""
        self._target_active = False

    def draw_target(self, frame) -> None:
        """Zeichnet das aktive Ziel (roter Kreis + Kreuz) auf den Frame."""
        if not self._target_active:
            return
        cx, cy, r = self._target_x, self._target_y, self._target_radius
        cv2.circle(frame, (cx, cy), r, (0, 0, 255), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        cv2.line(frame, (cx - r, cy), (cx + r, cy), (0, 0, 255), 1)
        cv2.line(frame, (cx, cy - r), (cx, cy + r), (0, 0, 255), 1)
        cv2.putText(frame, "TARGET", (cx - 28, cy - r - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)


    def draw_visual_markers(self, frame, nose_coords, left_iris_coords, right_iris_coords):
        """Markiert die Nase und die Iris-Zentren mit Kreisen"""
        if not self.show_debug:
            return
        
        h, w = frame.shape[:2]
        # Hilfsfunktion zur Umrechnung normalisierter Koordinaten in Pixel
        to_px = lambda coords: (int(coords[0] * w), int(coords[1] * h))

        # Markierung der Nasenspitze (Gelb)
        if nose_coords:
            cv2.circle(frame, to_px(nose_coords), 5, (0, 255, 255), -1)

        # Markierung der Iris-Zentren (Magenta)
        if left_iris_coords:
            cv2.circle(frame, to_px(left_iris_coords), 3, (255, 0, 255), -1)
        if right_iris_coords:
            cv2.circle(frame, to_px(right_iris_coords), 3, (255, 0, 255), -1)

    def draw_direction_crosshair(self, frame, nose_coords, delta_x, delta_y):
        """Zeichnet ein Fadenkreuz über das Gesicht, das die Bewegungsrichtung anzeigt"""
        if not self.show_debug or not nose_coords:
            return
            
        h, w = frame.shape[:2]
        center = (int(nose_coords[0] * w), int(nose_coords[1] * h))
        length = 60  # Länge der Achsen
        color = (0, 255, 0) # Grün
        
        # Zeichne das statische Fadenkreuz
        cv2.line(frame, (center[0] - length, center[1]), (center[0] + length, center[1]), color, 1)
        cv2.line(frame, (center[0], center[1] - length), (center[0], center[1] + length), color, 1)

        # Zeichne einen Indikator für die aktuelle Bewegungsrichtung (basierend auf den Deltas)
        # Die Deltas werden skaliert, um im Fadenkreuz sichtbar zu sein
        indicator_pos = (
            int(center[0] + (delta_x * 500)), 
            int(center[1] + (delta_y * 500))
        )
        cv2.line(frame, center, indicator_pos, (0, 0, 255), 2) # Roter Richtungsvektor
        cv2.circle(frame, indicator_pos, 4, (0, 0, 255), -1)

    def draw_tracking_info(self, frame, delta_x, delta_y, mouth_opening,
                           is_calibrated, iris_dx=0.0, iris_dy=0.0, fps=0.0):
        """Bestehende Text-Informationen zeichnen"""
        if not self.show_debug:
            return

        text_color   = tuple(self.config.get('colors.text', [255, 255, 255]))
        status_color = tuple(self.config.get(
            'colors.calibrated' if is_calibrated else 'colors.error', [0, 255, 0]
        ))

        status_text = "Status: AKTIV" if is_calibrated else "Status: KALIBRIERUNG"
        cv2.putText(frame, status_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, f"Head  dX: {delta_x:.3f}  dY: {delta_y:.3f}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        cv2.putText(frame, f"Iris  dX: {iris_dx:.4f}  dY: {iris_dy:.4f}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        cv2.putText(frame, f"Mouth: {mouth_opening:.3f}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        
        if fps > 0:
            fps_color = (0, 255, 0) if fps >= 24 else (0, 165, 255)
            cv2.putText(frame, f"FPS: {fps:.1f}",
                        (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 2)


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
        cv2.putText(frame, "ESC: Beenden | T: Neues Target spawnen", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
