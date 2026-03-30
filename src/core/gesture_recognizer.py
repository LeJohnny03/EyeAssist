"""Erweiterte Gesten-Erkennung mit konfigurierbaren Aktionen"""
import pyautogui

from utils import metrics_logger

class GestureRecognizer:
    """Erkennt verschiedene Gesichts-Gesten und führt Aktionen aus"""
    def __init__(self, config):
        self.config = config
        self.gesture_states = {}
        self.cooldowns = {}

        # Lade Gesten-Konfiguration
        self.gesture_actions = config.get_section('gesture_actions')
        self.load_gestures()

    def load_gestures(self):
        """Lädt Gesten-Konfiguration"""
        for gesture_name, settings in self.gesture_actions.items():
            self.gesture_states[gesture_name] = False
            self.cooldowns[gesture_name] = 0

    def update_cooldowns(self):
        """Update alle Cooldowns"""
        for gesture in self.cooldowns:
            if self.cooldowns[gesture] > 0:
                self.cooldowns[gesture] -= 1

    def detect_mouth_open(self, upper_lip, lower_lip):
        """Erkennt Mundöffnung"""
        if upper_lip is None or lower_lip is None:
            return 0.0
        return abs(upper_lip[1] - lower_lip[1])

    def detect_smile(self, left_mouth, right_mouth):
        """Erkennt Lächeln (Mundwinkel nach oben)"""
        if left_mouth is None or right_mouth is None:
            return 0.0
        # Vereinfachte Smile-Detection
        return abs(left_mouth[1] - right_mouth[1])

    def detect_head_tilt(self, nose_tip, reference_nose):
        """Erkennt Kopfneigung links/rechts"""
        if nose_tip is None or reference_nose is None:
            return 0.0
        return nose_tip[0] - reference_nose[0]

    def process_gestures(self, landmarks_data, metrics_logger=None):
        """
        Verarbeitet alle Gesten und führt Aktionen aus
        landmarks_data: dict mit allen relevanten Landmark-Positionen
        """
        self.update_cooldowns()
        detected_actions = []

        # Mundöffnung
        if 'mouth_open' in self.gesture_actions and self.gesture_actions['mouth_open']['enabled']:
            mouth_opening = self.detect_mouth_open(
                landmarks_data.get('upper_lip'),
                landmarks_data.get('lower_lip')
            )
            if self._check_gesture_trigger('mouth_open', mouth_opening):
                detected_actions.append(self.gesture_actions['mouth_open']['action'])

        # Sehr weite Mundöffnung
        if 'mouth_wide_open' in self.gesture_actions and self.gesture_actions['mouth_wide_open']['enabled']:
            mouth_opening = self.detect_mouth_open(
                landmarks_data.get('upper_lip'),
                landmarks_data.get('lower_lip')
            )
            if self._check_gesture_trigger('mouth_wide_open', mouth_opening):
                detected_actions.append(self.gesture_actions['mouth_wide_open']['action'])

        # Kopfneigung links
        if 'head_tilt_left' in self.gesture_actions and self.gesture_actions['head_tilt_left']['enabled']:
            tilt = self.detect_head_tilt(
                landmarks_data.get('nose_tip'),       # Nase bleibt für Tilt-Detection
                landmarks_data.get('reference_gaze')  # Referenz aus Gaze-Kalibrierung
            )
            if tilt < 0 and self._check_gesture_trigger('head_tilt_left', abs(tilt)):
                detected_actions.append(self.gesture_actions['head_tilt_left']['action'])

        # Kopfneigung rechts
        if 'head_tilt_right' in self.gesture_actions and self.gesture_actions['head_tilt_right']['enabled']:
            tilt = self.detect_head_tilt(
                landmarks_data.get('nose_tip'),
                landmarks_data.get('reference_nose')
            )
            if tilt > 0 and self._check_gesture_trigger('head_tilt_right', abs(tilt)):
                detected_actions.append(self.gesture_actions['head_tilt_right']['action'])

        # Führe Aktionen aus
        for action in detected_actions:
            self.execute_action(action, metrics_logger=metrics_logger)

        return detected_actions

    def _check_gesture_trigger(self, gesture_name, value):
        """Prüft ob Geste ausgelöst werden soll"""
        settings = self.gesture_actions[gesture_name]
        threshold = settings['threshold']
        cooldown_frames = settings['cooldown_frames']

        if value > threshold and self.cooldowns[gesture_name] == 0:
            if not self.gesture_states[gesture_name]:
                self.gesture_states[gesture_name] = True
                self.cooldowns[gesture_name] = cooldown_frames
                return True
        else:
            self.gesture_states[gesture_name] = False

        return False

    def execute_action(self, action, metrics_logger=None):
        """Führt konfigurierte Aktion aus"""
        if action == 'left_click':
            pyautogui.click()
            if metrics_logger is not None:
                metrics_logger.click_registered(x=pyautogui.position()[0], y=pyautogui.position()[1])
        elif action == 'right_click':
            pyautogui.rightClick()
        elif action == 'double_click':
            pyautogui.doubleClick()
        elif action == 'middle_click':
            pyautogui.middleClick()
        elif action == 'scroll_up':
            pyautogui.scroll(1)
        elif action == 'scroll_down':
            pyautogui.scroll(-1)
        elif action == 'drag_toggle':
            # Toggle drag mode
            pass  # TODO: Implementiere Drag-Modus
        elif action.startswith('key_'):
            key = action.replace('key_', '')
            pyautogui.press(key)

    def reset(self):
        """Setzt alle Gesten zurück"""
        for gesture in self.gesture_states:
            self.gesture_states[gesture] = False
            self.cooldowns[gesture] = 0

    def reload_config(self):
        """Lädt Konfiguration neu"""
        self.gesture_actions = self.config.get_section('gesture_actions')
        self.load_gestures()