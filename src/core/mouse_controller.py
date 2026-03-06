"""Maussteuerungs-Logik – Hybrid Head + Iris"""
import pyautogui
from utils.math_helpers import MovementSmoother, clamp, OneEuroFilter2D

class MouseController:
    """Steuert Maus basierend auf Kopfbewegung (grob) + Iris-Delta (fein)"""
    def __init__(self, config):
        self.config = config

        pyautogui.FAILSAFE = config.get('mouse.failsafe', True)
        pyautogui.PAUSE    = config.get('mouse.pause_duration', 0.001)

        self.screen_w, self.screen_h = pyautogui.size()

        # Kopf-Sensitivity (grobe Bewegung)
        self.sensitivity_x = config.get('mouse.sensitivity_x', 8.0)
        self.sensitivity_y = config.get('mouse.sensitivity_y', 10.0)

        # Iris-Sensitivity (Feinjustierung – bewusst klein halten)
        self.iris_sensitivity_x = config.get('mouse.iris_sensitivity_x', 3.0)
        self.iris_sensitivity_y = config.get('mouse.iris_sensitivity_y', 3.0)

        self.movement_threshold = config.get('mouse.movement_threshold', 0.002)
        self.invert_x = config.get('mouse.invert_x', False)
        self.invert_y = config.get('mouse.invert_y', False)

        self.reference_position = None
        self.calibrated = False

        min_cutoff = config.get('mouse.min_cutoff', 1.0)
        beta       = config.get('mouse.beta', 0.007)
        d_cutoff   = config.get('mouse.d_cutoff', 1.0)
        self.smoother = OneEuroFilter2D(mincutoff=min_cutoff, beta=beta, dcutoff=d_cutoff)

        self.pixel_deadzone = config.get('mouse.pixel_deadzone', 5)

    def set_reference_position(self, x, y):
        """Setzt Referenzposition für Kalibrierung (nur Kopf)"""
        self.reference_position = (x, y)
        self.calibrated = True
        self.smoother.clear()

    def reset_calibration(self):
        """Setzt Kalibrierung zurück"""
        self.reference_position = None
        self.calibrated = False
        self.smoother.clear()

    def move_mouse_hybrid(self, head_x, head_y, iris_delta_x=0.0, iris_delta_y=0.0):
        """
        Bewegt Maus: Kopf liefert grobe Richtung, Iris liefert Feinjustierung.
        head_x/y: normalisierte Nasenspitzen-Position aus MediaPipe
        iris_delta_x/y: Iris-Abweichung vom Augenmittelpunkt (sehr kleine Werte)
        """
        if not self.calibrated or self.reference_position is None:
            return False

        # Grobe Kopfbewegung relativ zur Kalibrierungsreferenz
        head_delta_x = head_x - self.reference_position[0]
        head_delta_y = head_y - self.reference_position[1]

        if self.invert_x:
            head_delta_x = -head_delta_x
        if self.invert_y:
            head_delta_y = -head_delta_y

        # Iris nur addieren wenn Kopf sich auch bewegt (verhindert Iris-Drift im Stillstand)
        if abs(head_delta_x) < self.movement_threshold and abs(head_delta_y) < self.movement_threshold:
            iris_delta_x = 0.0
            iris_delta_y = 0.0

        # Kombiniertes Delta: Kopf (grob) + Iris (fein)
        combined_x = head_delta_x * self.sensitivity_x + iris_delta_x * self.iris_sensitivity_x
        combined_y = head_delta_y * self.sensitivity_y + iris_delta_y * self.iris_sensitivity_y

        # Glättung anwenden
        self.smoother.add_point(combined_x, combined_y)
        smooth_x, smooth_y = self.smoother.get_smoothed()

        # Mausposition berechnen
        mouse_x = self.screen_w / 2 + smooth_x * self.screen_w
        mouse_y = self.screen_h / 2 + smooth_y * self.screen_h

        mouse_x = clamp(mouse_x, 0, self.screen_w - 1)
        mouse_y = clamp(mouse_y, 0, self.screen_h - 1)

        # Pixel-Deadzone
        current_mouse_x, current_mouse_y = pyautogui.position()
        dist = ((mouse_x - current_mouse_x) ** 2 + (mouse_y - current_mouse_y) ** 2) ** 0.5

        if dist < self.pixel_deadzone:
            return False

        pyautogui.moveTo(mouse_x, mouse_y)
        return True

    def move_mouse(self, current_x, current_y):
        """Fallback: nur Kopf, kein Iris (Abwärtskompatibilität)"""
        return self.move_mouse_hybrid(current_x, current_y, 0.0, 0.0)

    def click(self):
        """Führt Mausklick aus"""
        pyautogui.click()

    def get_delta(self, current_x, current_y):
        """Gibt Head-Delta zur Referenzposition zurück"""
        if not self.calibrated or self.reference_position is None:
            return 0, 0
        return (current_x - self.reference_position[0],
                current_y - self.reference_position[1])

    def update_sensitivity(self, sensitivity_x=None, sensitivity_y=None):
        """Aktualisiert Kopf-Empfindlichkeit"""
        if sensitivity_x is not None:
            self.sensitivity_x = sensitivity_x
        if sensitivity_y is not None:
            self.sensitivity_y = sensitivity_y
