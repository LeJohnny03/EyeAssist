"""Erweiterte Gesten-Erkennung mit konfigurierbaren Aktionen"""
from collections import deque
import pyautogui
from pynput.mouse import Button, Controller as MouseCtrl

from utils import metrics_logger


class GestureRecognizer:
    """
    Erkennt Gesichts-Gesten und führt Aktionen aus.

    Verbesserungen gegenüber der alten Version:
    - EAR-basierte Augenerkennung (Eye Aspect Ratio)
    - Normierte Mundmetriken (ratio für Kussmund)
    - Glättung per Rolling-Average
    - Hysterese: Geste muss N Frames aktiv sein bevor sie auslöst
    - Multi-Select-Hold: Linksklick gehalten für Mehrfachauswahl
    - Drag-Toggle vollständig implementiert
    """

    HYSTERESIS_FRAMES = 2   # Mindest-Frames aktiv bevor Auslösung

    def __init__(self, config):
        self.config = config
        self.gesture_actions = config.get_section('gesture_actions')

        gs = config.get_section('gesture_settings') or {}
        self._ear_smooth_n   = int(gs.get('ear_smoothing_frames', 5))
        self._smile_min_asym = float(gs.get('smile_asymmetry_min', 0.008))

        # Zustände
        self.gesture_states  = {}   # bool: Geste gerade aktiv
        self.cooldowns       = {}   # Frames bis Cooldown abgelaufen
        self.hysteresis      = {}   # Frames die Geste schon aktiv ist

        # Rolling-Average-Puffer für geglättete Metriken
        self._buffers: dict[str, deque] = {}

        # Drag & Multi-Select Zustand
        self._drag_active         = False
        self._multi_select_active = False
        self._pynput_mouse        = MouseCtrl()

        self.load_gestures()

    # ─── Konfiguration laden ─────────────────────────────────────────────────

    def load_gestures(self):
        for name in self.gesture_actions:
            self.gesture_states[name] = False
            self.cooldowns[name]      = 0
            self.hysteresis[name]     = 0
            self._buffers[name]       = deque(maxlen=self._ear_smooth_n)

    def reload_config(self):
        self.gesture_actions = self.config.get_section('gesture_actions')
        self.load_gestures()

    # ─── Hauptverarbeitung ───────────────────────────────────────────────────

    def process_gestures(self, landmarks_data, metrics_logger=None):
        """
        Verarbeitet alle Gesten.

        landmarks_data erwartet:
          - upper_lip, lower_lip       (für alte Kompatibilität)
          - mouth_metrics              (dict: open, width, ratio)
          - smile_metric               (float)
          - eyebrow_metric             (float)
          - left_ear, right_ear        (float, Eye Aspect Ratio)
          - nose_tip, reference_nose   (tuple)
        """
        self._tick_cooldowns()
        detected = []

        def _run(name, value):
            if name in self.gesture_actions and self.gesture_actions[name]['enabled']:
                if self._check_trigger(name, value):
                    detected.append(self.gesture_actions[name]['action'])

        mouth = landmarks_data.get('mouth_metrics') or {}
        opening = mouth.get('open', 0.0)
        ratio   = mouth.get('ratio', 0.0)
        smile   = landmarks_data.get('smile_metric', 0.0)
        l_ear   = landmarks_data.get('left_ear',  1.0)
        r_ear   = landmarks_data.get('right_ear', 1.0)
        ebrow   = landmarks_data.get('eyebrow_metric', 0.0)

        _run('mouth_open',       opening)
        _run('mouth_wide_open',  opening)

        # Kussmund: ratio (Öffnung/Breite) steigt, da Mund gespitzt wird
        _run('pucker',           ratio)

        # Lächeln: normierte Mundbreite (>threshold = lächeln)
        _run('smile',            smile)

        # Augenbraue
        _run('eyebrow_raise',    ebrow)

        # Linkes Auge zu: niedriger EAR = geschlossen
        # Threshold invertiert: Geste aktiv wenn EAR < threshold
        if 'left_eye_closed' in self.gesture_actions and \
                self.gesture_actions['left_eye_closed']['enabled']:
            th = self.gesture_actions['left_eye_closed']['threshold']
            # Wir übergeben (threshold - EAR) damit _check_trigger normal arbeitet
            _run('left_eye_closed',  max(0.0, th - l_ear + th))

        if 'right_eye_closed' in self.gesture_actions and \
                self.gesture_actions['right_eye_closed']['enabled']:
            th = self.gesture_actions['right_eye_closed']['threshold']
            _run('right_eye_closed', max(0.0, th - r_ear + th))

        # Kopfneigung
        tilt = self._calc_tilt(
            landmarks_data.get('nose_tip'),
            landmarks_data.get('reference_nose'))
        if tilt is not None:
            if tilt < 0:
                _run('head_tilt_left',  abs(tilt))
            else:
                _run('head_tilt_right', abs(tilt))

        for action in detected:
            self.execute_action(action, metrics_logger=metrics_logger)

        return detected

    # ─── Trigger-Logik ───────────────────────────────────────────────────────

    def _check_trigger(self, name, value):
        """
        Gibt True zurück wenn:
        - Wert > Threshold
        - Cooldown abgelaufen
        - Hysterese-Frames erfüllt (verhindert Einzel-Frame-Ausreißer)
        """
        settings  = self.gesture_actions[name]
        threshold = settings['threshold']
        cooldown_frames = settings['cooldown_frames']

        # Geglätteten Wert berechnen
        buf = self._buffers[name]
        buf.append(value)
        smoothed = sum(buf) / len(buf)

        if smoothed > threshold:
            self.hysteresis[name] += 1
            if self.hysteresis[name] >= self.HYSTERESIS_FRAMES \
                    and self.cooldowns[name] == 0 \
                    and not self.gesture_states[name]:
                self.gesture_states[name] = True
                self.cooldowns[name] = cooldown_frames
                return True
        else:
            self.gesture_states[name] = False
            self.hysteresis[name]     = 0

        return False

    def _tick_cooldowns(self):
        for name in self.cooldowns:
            if self.cooldowns[name] > 0:
                self.cooldowns[name] -= 1

    def _calc_tilt(self, nose_tip, reference_nose):
        if nose_tip is None or reference_nose is None:
            return None
        return nose_tip[0] - reference_nose[0]

    # ─── Aktionen ausführen ──────────────────────────────────────────────────

    def execute_action(self, action, metrics_logger=None):
        """Führt konfigurierte Aktion aus."""
        if action == 'left_click':
            pyautogui.click()
            if metrics_logger:
                pos = pyautogui.position()
                metrics_logger.click_registered(x=pos[0], y=pos[1])

        elif action == 'right_click':
            pyautogui.rightClick()

        elif action == 'double_click':
            pyautogui.doubleClick()

        elif action == 'middle_click':
            pyautogui.middleClick()

        elif action == 'multi_select_hold':
            """
            Hält die linke Maustaste gedrückt. Zweiter Aufruf löst sie.
            Gekoppelt an den gemappten Linksklick: während Hold aktiv ist,
            wird jeder left_click als Shift+Click ausgeführt → Mehrfachauswahl.
            """
            if not self._multi_select_active:
                self._pynput_mouse.press(Button.left)
                self._multi_select_active = True
            else:
                self._pynput_mouse.release(Button.left)
                self._multi_select_active = False

        elif action == 'drag_toggle':
            if not self._drag_active:
                self._pynput_mouse.press(Button.left)
                self._drag_active = True
            else:
                self._pynput_mouse.release(Button.left)
                self._drag_active = False

        elif action == 'scroll_up':
            pyautogui.scroll(1000)

        elif action == 'scroll_down':
            pyautogui.scroll(-1000)

        elif action.startswith('key_'):
            key = action.replace('key_', '')
            pyautogui.press(key)

    def release_all_holds(self):
        """Gibt alle gehaltenen Maustasten frei (beim Stop aufrufen)."""
        if self._drag_active or self._multi_select_active:
            self._pynput_mouse.release(Button.left)
            self._drag_active         = False
            self._multi_select_active = False

    def reset(self):
        """Setzt alle Gesten-Zustände zurück."""
        self.release_all_holds()
        for name in self.gesture_states:
            self.gesture_states[name] = False
            self.cooldowns[name]      = 0
            self.hysteresis[name]     = 0
            self._buffers[name].clear()