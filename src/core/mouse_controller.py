"""Maussteuerungs-Logik"""
import pyautogui
from utils.math_helpers import MovementSmoother, clamp, OneEuroFilter2D

class MouseController:
    """Steuert Maus basierend auf Kopfbewegungen"""
    def __init__(self, config):
        self.config = config

        # PyAutoGUI Einstellungen aus Config
        pyautogui.FAILSAFE = config.get('mouse.failsafe', True)
        pyautogui.PAUSE = config.get('mouse.pause_duration', 0.001)

        self.screen_w, self.screen_h = pyautogui.size()
        self.sensitivity_x = config.get('mouse.sensitivity_x', 2.5)
        self.sensitivity_y = config.get('mouse.sensitivity_y', 2.5)
        self.movement_threshold = config.get('mouse.movement_threshold', 0.002)
        self.invert_x = config.get('mouse.invert_x', False)
        self.invert_y = config.get('mouse.invert_y', False)

        # Kalibrierung
        self.reference_position = None
        self.calibrated = False

        # Moving Average Bewegungsglättung
        # smoothing_size = config.get('mouse.smoothing_buffer_size', 5)
        # self.smoother = MovementSmoother(smoothing_size)
        
        # 1€-Filter Bewegungsglättung
        min_cutoff = config.get('mouse.min_cutoff', 1.0)
        beta       = config.get('mouse.beta', 0.007)
        d_cutoff   = config.get('mouse.d_cutoff', 1.0)
        self.smoother = OneEuroFilter2D(mincutoff=min_cutoff, beta=beta, dcutoff=d_cutoff)
        # Pixel-Deadzone: Cursor bewegt sich nur, wenn Ziel > N px entfernt ist
        self.pixel_deadzone = config.get('mouse.pixel_deadzone', 4)

    def set_reference_position(self, x, y):
        """Setzt Referenzposition für Kalibrierung"""
        self.reference_position = (x, y)
        self.calibrated = True
        self.smoother.clear()

    def reset_calibration(self):
        """Setzt Kalibrierung zurück"""
        self.reference_position = None
        self.calibrated = False
        self.smoother.clear()

    def move_mouse(self, current_x, current_y):
        """Bewegt Maus basierend auf Kopfposition"""
        if not self.calibrated or self.reference_position is None:
            return False

        # Relative Bewegung zur Referenz
        delta_x = current_x - self.reference_position[0]
        delta_y = current_y - self.reference_position[1]

        # Invertierung anwenden
        if self.invert_x:
            delta_x = -delta_x
        if self.invert_y:
            delta_y = -delta_y

        # Bewegungsschwelle prüfen
        if abs(delta_x) < self.movement_threshold and abs(delta_y) < self.movement_threshold:
            return False

        # Glättung anwenden
        self.smoother.add_point(delta_x, delta_y)
        smooth_x, smooth_y = self.smoother.get_smoothed()

        # Mausposition berechnen (invertierte Y-Achse für natürliche Bewegung)
        mouse_x = self.screen_w / 2 + smooth_x * self.screen_w * self.sensitivity_x
        mouse_y = self.screen_h / 2 + smooth_y * self.screen_h * self.sensitivity_y

        # Bildschirmgrenzen beachten
        mouse_x = clamp(mouse_x, 0, self.screen_w - 1)
        mouse_y = clamp(mouse_y, 0, self.screen_h - 1)
        
        # Pixel-Deadzone: aktuelle Mausposition mit Zielposition vergleichen
        current_mouse_x, current_mouse_y = pyautogui.position()
        dist = ((mouse_x - current_mouse_x) ** 2 + (mouse_y - current_mouse_y) ** 2) ** 0.5
        
        # Zu kleine Bewegungen ignorieren
        if dist < self.pixel_deadzone:
            return False 

        # Maus bewegen
        pyautogui.moveTo(mouse_x, mouse_y)
        return True

    def click(self):
        """Führt Mausklick aus"""
        pyautogui.click()

    def get_delta(self, current_x, current_y):
        """Gibt Delta zur Referenzposition zurück"""
        if not self.calibrated or self.reference_position is None:
            return 0, 0
        return (current_x - self.reference_position[0], 
                current_y - self.reference_position[1])

    def update_sensitivity(self, sensitivity_x=None, sensitivity_y=None):
        """Aktualisiert Empfindlichkeit"""
        if sensitivity_x is not None:
            self.sensitivity_x = sensitivity_x
        if sensitivity_y is not None:
            self.sensitivity_y = sensitivity_y