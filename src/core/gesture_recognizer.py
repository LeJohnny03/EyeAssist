import math
import time
from .tracker_engine import TrackResult


class GestureRecognizer:
    """
    - Linkes Auge blinzeln -> LEFT_CLICK
    - Beide Augen X Sekunden geschlossen -> STOP_CONTROL
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg

        # Blink (links)
        self.cooldown = 0
        self.blink_detected = False

        # Both-eyes close hold
        self._both_closed_since = None

        # Debug
        self.last_left_eye_dist = None
        self.last_right_eye_dist = None
        self.last_event = None

    def update(self, track: TrackResult) -> str | None:
        self.last_event = None

        if not track.has_face:
            self._both_closed_since = None
            self.last_left_eye_dist = None
            self.last_right_eye_dist = None
            return None

        # ---- Eye distances (normalized) ----
        if track.left_eye_top and track.left_eye_bottom:
            self.last_left_eye_dist = math.dist(track.left_eye_top, track.left_eye_bottom)
        else:
            self.last_left_eye_dist = None

        if track.right_eye_top and track.right_eye_bottom:
            self.last_right_eye_dist = math.dist(track.right_eye_top, track.right_eye_bottom)
        else:
            self.last_right_eye_dist = None

        # ---- 1) Both eyes closed -> STOP_CONTROL ----
        both_thr = self.cfg["gestures"]["both_eyes_threshold"]
        hold_s = self.cfg["gestures"]["both_eyes_close_seconds"]

        both_available = (self.last_left_eye_dist is not None) and (self.last_right_eye_dist is not None)
        both_closed = both_available and (self.last_left_eye_dist < both_thr) and (self.last_right_eye_dist < both_thr)

        now = time.time()
        if both_closed:
            if self._both_closed_since is None:
                self._both_closed_since = now
            else:
                if (now - self._both_closed_since) >= hold_s:
                    # Event feuern und resetten, damit es nicht dauer-spammt
                    self._both_closed_since = None
                    self.last_event = "STOP_CONTROL"
                    return "STOP_CONTROL"
        else:
            self._both_closed_since = None

        # ---- 2) Left blink -> click ----
        # (nur wenn beide Augen Geste nicht gerade getriggert hat)
        if self.last_left_eye_dist is None:
            return None

        thr = self.cfg["blink"]["threshold"]
        hysteresis = self.cfg["blink"]["hysteresis"]
        cooldown_frames = self.cfg["blink"]["cooldown_frames"]

        if self.cooldown > 0:
            self.cooldown -= 1

        if self.last_left_eye_dist < thr and self.cooldown == 0:
            if not self.blink_detected:
                self.blink_detected = True
                self.cooldown = cooldown_frames
                self.last_event = "LEFT_CLICK"
                return "LEFT_CLICK"
        else:
            if self.last_left_eye_dist > (thr + hysteresis):
                self.blink_detected = False

        return None
