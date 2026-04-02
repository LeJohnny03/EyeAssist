"""Erweiterte Gesten-Erkennung mit konfigurierbaren Aktionen"""
import time
import pyautogui

from utils import metrics_logger


class GestureRecognizer:
    """Erkennt verschiedene Gesichts-Gesten und führt Aktionen aus"""

    # Schwellwert: Mundbreite unter diesem Faktor des Kalibrierungs-Wertes
    # gilt als "gespitzt" (Puckered). Typischer Wert: 0.75 (25% schmaler)
    PUCKER_WIDTH_RATIO = 0.75

    def __init__(self, config):
        self.config = config
        self.gesture_states = {}
        self.cooldowns = {}

        # Für Drag-Logik
        self._drag_active = False
        self._mouth_open_start_time = None
        self._drag_hold_threshold = config.get('gesture_actions.mouth_open.drag_hold_seconds', 0.8)

        # Kalibrierter Mundbreiten-Referenzwert (wird beim ersten Erkennen gesetzt)
        self._calibrated_mouth_width = None

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

    # ------------------------------------------------------------------ #
    #  Erkennungs-Hilfsmethoden                                           #
    # ------------------------------------------------------------------ #

    def detect_mouth_open(self, upper_lip, lower_lip):
        """Gibt vertikale Mundöffnung zurück"""
        if upper_lip is None or lower_lip is None:
            return 0.0
        return abs(upper_lip[1] - lower_lip[1])

    def detect_puckered_mouth(self, upper_lip, lower_lip, mouth_width):
        """
        Erkennt gespitzte Lippen (Puckered/Kussmund).
        Kriterien:
          1. Mund ist leicht geöffnet (vertikale Öffnung > kleinem Mindestschwellwert)
          2. Mundbreite deutlich kleiner als kalibrierter Referenzwert
        Gibt True zurück wenn Geste erkannt wird.
        """
        if upper_lip is None or lower_lip is None or mouth_width is None:
            return False

        vertical_opening = abs(upper_lip[1] - lower_lip[1])

        # Kalibrierung: ersten gültigen Messwert als Referenz speichern
        if self._calibrated_mouth_width is None:
            self._calibrated_mouth_width = mouth_width
            return False

        # Mundbreiten-Verhältnis berechnen
        width_ratio = mouth_width / self._calibrated_mouth_width

        # Puckered = leicht offen UND deutlich schmaler
        is_puckered = (
            vertical_opening > 0.005   # Mund minimal geöffnet (kein geschlossener Mund)
            and width_ratio < self.PUCKER_WIDTH_RATIO  # Lippen zusammengezogen
        )
        return is_puckered

    def is_mouth_normal_open(self, upper_lip, lower_lip, mouth_width):
        """
        Prüft ob der Mund normal (nicht gespitzt) geöffnet ist.
        Schließt Puckered-Mund explizit aus.
        """
        if upper_lip is None or lower_lip is None or mouth_width is None:
            return False

        vertical_opening = abs(upper_lip[1] - lower_lip[1])
        if vertical_opening <= self.gesture_actions.get('mouth_open', {}).get('threshold', 0.03):
            return False

        # Nur auslösen wenn Mund NICHT gespitzt ist
        if self._calibrated_mouth_width is not None:
            width_ratio = mouth_width / self._calibrated_mouth_width
            if width_ratio < self.PUCKER_WIDTH_RATIO:
                return False  # Puckered → nicht als mouth_open zählen

        return True

    def detect_smile(self, left_mouth, right_mouth, face_width):
        """
        Erkennt Lächeln: Mundbreite im Verhältnis zur Gesichtsbreite.
        Zuverlässiger als reine Y-Differenz der Mundwinkel.
        """
        if left_mouth is None or right_mouth is None or face_width is None or face_width == 0:
            return 0.0
        mouth_width = abs(right_mouth[0] - left_mouth[0])
        return mouth_width / face_width

    def detect_head_tilt(self, eye_roll_angle):
        """
        Gibt echten Roll-Winkel des Kopfes zurück (in Grad).
        Positiv = Kopf nach rechts geneigt, Negativ = nach links.
        Verwendet den Augen-Roll-Winkel aus TrackerEngine.
        """
        return eye_roll_angle if eye_roll_angle is not None else 0.0

    def detect_eyebrow_raise(self, left_eyebrow, left_eye_top, right_eyebrow, right_eye_top):
        """
        Erkennt Augenbrauen hochziehen.
        Misst Abstand Augenbraue → Auge relativ normiert.
        """
        if None in (left_eyebrow, left_eye_top, right_eyebrow, right_eye_top):
            return 0.0
        left_dist  = abs(left_eyebrow[1]  - left_eye_top[1])
        right_dist = abs(right_eyebrow[1] - right_eye_top[1])
        return (left_dist + right_dist) / 2.0

    # ------------------------------------------------------------------ #
    #  Haupt-Verarbeitungsschleife                                        #
    # ------------------------------------------------------------------ #

    def process_gestures(self, landmarks_data, metrics_logger=None):
        """
        Verarbeitet alle Gesten und führt Aktionen aus.
        landmarks_data: dict mit allen relevanten Landmark-Positionen
        """
        self.update_cooldowns()
        detected_actions = []

        upper_lip   = landmarks_data.get('upper_lip')
        lower_lip   = landmarks_data.get('lower_lip')
        mouth_width = landmarks_data.get('mouth_width')

        # ---- Mouth Open (normaler Klick + Drag) -------------------------
        if 'mouth_open' in self.gesture_actions and self.gesture_actions['mouth_open']['enabled']:
            mouth_is_open = self.is_mouth_normal_open(upper_lip, lower_lip, mouth_width)
            self._handle_mouth_open_drag(mouth_is_open, detected_actions)

        # ---- Puckered Mouth (Kussmund / gespitzte Lippen) ---------------
        if 'puckered_mouth' in self.gesture_actions and self.gesture_actions['puckered_mouth']['enabled']:
            is_puckered = self.detect_puckered_mouth(upper_lip, lower_lip, mouth_width)
            if is_puckered and self._check_gesture_trigger('puckered_mouth', 1.0):
                detected_actions.append(self.gesture_actions['puckered_mouth']['action'])

        # ---- Smile -------------------------------------------------------
        if 'smile' in self.gesture_actions and self.gesture_actions['smile']['enabled']:
            left_mouth  = landmarks_data.get('mouth_left')
            right_mouth = landmarks_data.get('mouth_right')
            face_width  = landmarks_data.get('face_width')
            smile_value = self.detect_smile(left_mouth, right_mouth, face_width)
            if self._check_gesture_trigger('smile', smile_value):
                detected_actions.append(self.gesture_actions['smile']['action'])

        # ---- Augenbrauen hochziehen --------------------------------------
        if 'eyebrow_raise' in self.gesture_actions and self.gesture_actions['eyebrow_raise']['enabled']:
            eyebrow_val = self.detect_eyebrow_raise(
                landmarks_data.get('left_eyebrow'),
                landmarks_data.get('left_eye_top'),
                landmarks_data.get('right_eyebrow'),
                landmarks_data.get('right_eye_top')
            )
            if self._check_gesture_trigger('eyebrow_raise', eyebrow_val):
                detected_actions.append(self.gesture_actions['eyebrow_raise']['action'])

        # ---- Kopf nach links geneigt (echter Roll-Winkel) ----------------
        if 'head_tilt_left' in self.gesture_actions and self.gesture_actions['head_tilt_left']['enabled']:
            roll = self.detect_head_tilt(landmarks_data.get('eye_roll_angle'))
            # Negativ = nach links geneigt (Augen-Linie fällt von links nach rechts)
            if roll < 0 and self._check_gesture_trigger('head_tilt_left', abs(roll)):
                detected_actions.append(self.gesture_actions['head_tilt_left']['action'])

        # ---- Kopf nach rechts geneigt (echter Roll-Winkel) ---------------
        if 'head_tilt_right' in self.gesture_actions and self.gesture_actions['head_tilt_right']['enabled']:
            roll = self.detect_head_tilt(landmarks_data.get('eye_roll_angle'))
            if roll > 0 and self._check_gesture_trigger('head_tilt_right', abs(roll)):
                detected_actions.append(self.gesture_actions['head_tilt_right']['action'])

        # Führe Aktionen aus
        for action in detected_actions:
            self.execute_action(action, metrics_logger=metrics_logger)

        return detected_actions

    # ------------------------------------------------------------------ #
    #  Drag-Logik (langes Mund-Öffnen)                                   #
    # ------------------------------------------------------------------ #

    def _handle_mouth_open_drag(self, mouth_is_open, detected_actions):
        """
        Steuert Klick- und Drag-Verhalten bei Mundöffnung:
          - Kurzes Öffnen + Schließen → normaler Linksklick
          - Mund geöffnet halten (> drag_hold_seconds) → mouseDown (Drag beginnt)
          - Mund schließen nach langem Halten → mouseUp (Drag endet)
        """
        now = time.time()

        if mouth_is_open:
            if self._mouth_open_start_time is None:
                # Mund gerade geöffnet
                self._mouth_open_start_time = now

            held_duration = now - self._mouth_open_start_time

            if not self._drag_active and held_duration >= self._drag_hold_threshold:
                # Drag-Modus starten
                self._drag_active = True
                pyautogui.mouseDown(button='left')
                # Keine Action in detected_actions – mouseDown direkt ausführen

        else:
            # Mund geschlossen
            if self._mouth_open_start_time is not None:
                held_duration = now - self._mouth_open_start_time

                if self._drag_active:
                    # Drag beenden
                    self._drag_active = False
                    pyautogui.mouseUp(button='left')
                elif held_duration < self._drag_hold_threshold and self.cooldowns.get('mouth_open', 0) == 0:
                    # Kurzes Öffnen → normaler Klick
                    detected_actions.append(self.gesture_actions['mouth_open']['action'])
                    self.cooldowns['mouth_open'] = self.gesture_actions['mouth_open'].get('cooldown_frames', 15)

                self._mouth_open_start_time = None

    # ------------------------------------------------------------------ #
    #  Hilfsmethoden                                                      #
    # ------------------------------------------------------------------ #

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
            pyautogui.scroll(1000)
        elif action == 'scroll_down':
            pyautogui.scroll(-1000)
        elif action.startswith('key_'):
            key = action.replace('key_', '')
            pyautogui.press(key)

    def reset(self):
        """Setzt alle Gesten zurück"""
        if self._drag_active:
            pyautogui.mouseUp(button='left')
            self._drag_active = False
        self._mouth_open_start_time = None
        for gesture in self.gesture_states:
            self.gesture_states[gesture] = False
            self.cooldowns[gesture] = 0

    def reload_config(self):
        """Lädt Konfiguration neu"""
        self.gesture_actions = self.config.get_section('gesture_actions')
        self.load_gestures()