import cv2
import numpy as np
import time
import math
import csv
import os
from datetime import datetime

try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = False
except Exception:
    HAS_PYAUTOGUI = False

import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh

# Importiere deinen Metrics Logger
#from MetricsLogger import MetricsLogger

# ---------------------------
# MediaPipe landmark indices
# ---------------------------
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

HP_NOSE = 1
HP_CHIN = 152
HP_LEYE = 33
HP_REYE = 263
HP_LMOUTH = 61
HP_RMOUTH = 291


# ---------------------------
# Utilities
# ---------------------------
def lm_to_xy(landmarks, idx, w, h):
    lm = landmarks[idx]
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)

def iris_center(landmarks, indices, w, h):
    pts = np.stack([lm_to_xy(landmarks, i, w, h) for i in indices], axis=0)
    return pts.mean(axis=0)

def safe_norm(v, eps=1e-6):
    n = np.linalg.norm(v)
    return v / (n + eps)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class MetricsLogger:
    """Schreibt TTT- und Framerate-Metriken in eine CSV-Datei."""

    CSV_HEADER = [
        "timestamp_iso",        # Absoluter Zeitstempel (ISO-8601)
        "event_type",           # 'frame' | 'target_appeared' | 'click_registered'
        "frame_latency_ms",     # Capture→Injection Latenz in ms  (nur bei 'frame')
        "fps",                  # Gleitender FPS-Wert             (nur bei 'frame')
        "cursor_delta_x",       # Cursor-Delta in x               (nur bei 'frame')
        "cursor_delta_y",       # Cursor-Delta in y               (nur bei 'frame')
        "x",                    # X-Koordinate des Cursors          (nur bei 'frame')
        "y",                    # Y-Koordinate des Cursors          (nur bei 'frame')
        "ttt_ms",               # Time-to-Target in ms  (nur bei 'click_registered')
    ]

    def __init__(self, output_dir: str = "metrics", enabled: bool = True):
        self.enabled = enabled
        self._target_appear_time: float | None = None
        self._frame_start_time:   float | None = None
        self._last_frame_time:    float | None = None
        self._fps_alpha = 0.1          # EMA-Gewicht für gleitenden FPS
        self._fps_ema:  float = 0.0

        if not self.enabled:
            self._file = None
            self._writer = None
            return

        os.makedirs(output_dir, exist_ok=True)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"metrics_{session_ts}.csv")

        self._file   = open(filepath, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.CSV_HEADER)
        self._writer.writeheader()
        self._file.flush()

    # ------------------------------------------------------------------
    # Metrik 2: System-Latenz & Framerate
    # ------------------------------------------------------------------

    def frame_start(self) -> None:
        """Muss zu Beginn jeder Frame-Verarbeitung aufgerufen werden."""
        self._frame_start_time = time.perf_counter()

    def frame_end(self, cursor_delta_x: float = 0.0,
                  cursor_delta_y: float = 0.0, x: float = 0.0, y: float = 0.0) -> None:
        """Muss am Ende der Frame-Verarbeitung aufgerufen werden.

        Parameters
        ----------
        cursor_delta_x/y : Head-Delta zur Referenzposition (aus MouseController).
        x/y : X- und Y-Koordinaten des Cursors.
        """
        if not self.enabled or self._frame_start_time is None:
            return

        now = time.perf_counter()
        latency_ms = (now - self._frame_start_time) * 1000.0

        # Gleitender FPS-Durchschnitt via Exponential Moving Average
        if self._last_frame_time is not None:
            instant_fps = 1.0 / max(now - self._last_frame_time, 1e-9)
            self._fps_ema = (
                instant_fps if self._fps_ema == 0.0
                else (1 - self._fps_alpha) * self._fps_ema
                     + self._fps_alpha * instant_fps
            )
        self._last_frame_time = now

        self._write_row(
            event_type="frame",
            frame_latency_ms=round(latency_ms, 3),
            fps=round(self._fps_ema, 2),
            cursor_delta_x=round(cursor_delta_x, 6),
            cursor_delta_y=round(cursor_delta_y, 6),
            x=round(x, 2),
            y=round(y, 2),
        )

    # ------------------------------------------------------------------
    # Metrik 1: Time-to-Target (TTT)
    # ------------------------------------------------------------------

    def target_appeared(self) -> None:
        """Markiert den Zeitpunkt, zu dem ein Ziel sichtbar wird."""
        if not self.enabled:
            return
        self._target_appear_time = time.perf_counter()
        self._write_row(event_type="target_appeared")
        
    def has_active_target(self) -> bool:
        """True solange das Target noch nicht geklickt wurde."""
        return self._target_appear_time is not None

    def click_registered(self, x: float = 0.0, y: float = 0.0) -> None:
        """Markiert einen Linksklick und berechnet TTT."""
        if not self.enabled:
            return

        ttt_ms: float | None = None
        if self._target_appear_time is not None:
            ttt_ms = (time.perf_counter() - self._target_appear_time) * 1000.0
            self._target_appear_time = None   # Reset nach Registrierung

        self._write_row(
            event_type="click_registered",
            x=round(x, 2),
            y=round(y, 2),
            ttt_ms=round(ttt_ms, 3) if ttt_ms is not None else None,
        )

    # ------------------------------------------------------------------
    # Interne Hilfsmethoden
    # ------------------------------------------------------------------

    def _write_row(self, **kwargs) -> None:
        if not self.enabled or self._writer is None:
            return
        row = {col: "" for col in self.CSV_HEADER}
        row["timestamp_iso"] = datetime.now().isoformat(timespec="milliseconds")
        row.update(kwargs)
        self._writer.writerow(row)
        self._file.flush()

    def get_fps(self) -> float:
        """Gibt den aktuellen EMA-FPS-Wert zurück (z. B. für das Overlay)."""
        return round(self._fps_ema, 1)

    def close(self) -> None:
        """Schließt die CSV-Datei."""
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None

# ---------------------------
# One Euro Filter (2D)
# ---------------------------
class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.01, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None
        
    def reset(self, x=None, t=None):
        self.x_prev = None if x is None else np.array(x, dtype=np.float32)
        self.dx_prev = None if x is None else np.zeros_like(self.x_prev)
        self.t_prev = t

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def _lowpass(self, x, x_prev, alpha):
        return alpha * x + (1.0 - alpha) * x_prev

    def update(self, x, t):
        x = np.array(x, dtype=np.float32)
        if self.t_prev is None:
            self.t_prev = t
            self.x_prev = x
            self.dx_prev = np.zeros_like(x)
            return x

        dt = float(t - self.t_prev)
        self.t_prev = t

        dx = (x - self.x_prev) / max(dt, 1e-6)
        alpha_d = self._alpha(self.d_cutoff, dt)
        dx_hat = self._lowpass(dx, self.dx_prev, alpha_d)
        self.dx_prev = dx_hat

        cutoff = self.min_cutoff + self.beta * float(np.linalg.norm(dx_hat))
        alpha = self._alpha(cutoff, dt)

        x_hat = self._lowpass(x, self.x_prev, alpha)
        self.x_prev = x_hat
        return x_hat


# ---------------------------
# Gaze feature extraction
# ---------------------------
def gaze_features(landmarks, w, h):
    l_outer = lm_to_xy(landmarks, LEFT_EYE_OUTER, w, h)
    l_inner = lm_to_xy(landmarks, LEFT_EYE_INNER, w, h)
    r_inner = lm_to_xy(landmarks, RIGHT_EYE_INNER, w, h)
    r_outer = lm_to_xy(landmarks, RIGHT_EYE_OUTER, w, h)

    l_iris = iris_center(landmarks, LEFT_IRIS, w, h)
    r_iris = iris_center(landmarks, RIGHT_IRIS, w, h)

    l_axis = (l_inner - l_outer)
    r_axis = (r_outer - r_inner)

    l_w = np.linalg.norm(l_axis) + 1e-6
    r_w = np.linalg.norm(r_axis) + 1e-6

    l_x = np.dot((l_iris - l_outer), safe_norm(l_axis)) / l_w
    r_x = np.dot((r_iris - r_inner), safe_norm(r_axis)) / r_w

    l_mid = 0.5 * (l_outer + l_inner)
    r_mid = 0.5 * (r_inner + r_outer)
    l_y = (l_iris[1] - l_mid[1]) / l_w
    r_y = (r_iris[1] - r_mid[1]) / r_w

    feats = np.array([l_x, l_y, r_x, r_y], dtype=np.float32)
    feats = np.clip(feats, -2.0, 2.0)

    return feats, (l_iris, r_iris, l_outer, l_inner, r_inner, r_outer)


# ---------------------------
# Head pose estimation (solvePnP)
# ---------------------------
def rotation_matrix_to_euler(R):
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6
    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0.0
    return np.array([y, x, z], dtype=np.float32)

def estimate_head_pose(landmarks, w, h):
    image_points = np.array([
        lm_to_xy(landmarks, HP_NOSE, w, h),
        lm_to_xy(landmarks, HP_CHIN, w, h),
        lm_to_xy(landmarks, HP_LEYE, w, h),
        lm_to_xy(landmarks, HP_REYE, w, h),
        lm_to_xy(landmarks, HP_LMOUTH, w, h),
        lm_to_xy(landmarks, HP_RMOUTH, w, h),
    ], dtype=np.float32)

    model_points = np.array([
        [0.0,   0.0,   0.0],
        [0.0, -63.0, -12.0],
        [-43.0, 32.0, -26.0],
        [43.0,  32.0, -26.0],
        [-28.0, -28.0, -24.0],
        [28.0,  -28.0, -24.0],
    ], dtype=np.float32)

    focal_length = w
    center = (w / 2.0, h / 2.0)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float32)

    dist_coeffs = np.zeros((4, 1), dtype=np.float32)

    ok, rvec, tvec = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not ok:
        return None

    R, _ = cv2.Rodrigues(rvec)
    ypr = rotation_matrix_to_euler(R)
    ypr = np.clip(ypr, -1.2, 1.2)
    return ypr


# ---------------------------
# Polynomial feature expansion (degree 2)
# ---------------------------
def poly2_expand(x):
    x = np.asarray(x, dtype=np.float32)
    D = x.shape[0]
    feats = [x]
    feats.append(x * x)
    prods = []
    for i in range(D):
        for j in range(i + 1, D):
            prods.append(x[i] * x[j])
    if prods:
        feats.append(np.array(prods, dtype=np.float32))
    return np.concatenate(feats, axis=0)

# ---------------------------
# Calibrator (Ridge regression)
# ---------------------------
class Calibrator:
    def __init__(self, ridge_lam=1e-2):
        self.ridge_lam = float(ridge_lam)
        self.X = []
        self.Y = []
        self.W = None

    def add_sample(self, feats, screen_xy):
        self.X.append(np.append(feats, 1.0))
        self.Y.append(screen_xy)

    def fit(self):
        if len(self.X) < 20:
            return False
        X = np.stack(self.X, axis=0).astype(np.float32)
        Y = np.stack(self.Y, axis=0).astype(np.float32)

        lam = self.ridge_lam
        A = X.T @ X + lam * np.eye(X.shape[1], dtype=np.float32)
        B = X.T @ Y
        self.W = np.linalg.solve(A, B)
        return True

    def predict(self, feats):
        if self.W is None:
            return None
        x = np.append(feats, 1.0).astype(np.float32)
        return x @ self.W


# ---------------------------
# Calibration points (13 points)
# ---------------------------
def make_calib_points_13(sw, sh, margin=0.10):
    xs = [margin, 0.5, 1 - margin]
    ys = [margin, 0.5, 1 - margin]
    pts = []
    for y in ys:
        for x in xs:
            pts.append((int(x * sw), int(y * sh)))

    pts.append((int(0.5 * sw), int(margin * sh)))
    pts.append((int(0.5 * sw), int((1 - margin) * sh)))
    pts.append((int(margin * sw), int(0.5 * sh)))
    pts.append((int((1 - margin) * sw), int(0.5 * sh)))

    uniq = []
    seen = set()
    for p in pts:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq


def draw_target(canvas, x, y, label=None):
    # Radius auf 100 Pixel erhöht (vorher 30)
    cv2.circle(canvas, (int(x), int(y)), 100, (0, 255, 255), 3)
    cv2.circle(canvas, (int(x), int(y)), 6, (0, 255, 255), -1)
    if label:
        cv2.putText(canvas, label, (int(x) + 110, int(y) - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)


# ---------------------------
# Stability & Filtering
# ---------------------------
class StabilityGate:
    def __init__(self, window=12):
        self.window = int(window)
        self.buf = []

    def push(self, x):
        x = np.array(x, dtype=np.float32)
        self.buf.append(x)
        if len(self.buf) > self.window:
            self.buf.pop(0)

    def stable(self, thresh=0.012):
        if len(self.buf) < self.window:
            return False
        X = np.stack(self.buf, axis=0)
        std = float(np.mean(np.std(X, axis=0)))
        return std < thresh


class JumpGate:
    def __init__(self, max_step_px=45.0):
        self.max_step = float(max_step_px)
        self.last = None

    def update(self, p):
        p = np.array(p, dtype=np.float32)
        if self.last is None:
            self.last = p
            return p

        d = float(np.linalg.norm(p - self.last))
        if d <= self.max_step:
            self.last = p
            return p

        direction = (p - self.last) / max(d, 1e-6)
        self.last = self.last + direction * self.max_step
        return self.last


class Deadzone:
    def __init__(self, radius_px=3):
        self.r = float(radius_px)
        self.anchor = None

    def reset(self):
        self.anchor = None

    def update(self, p):
        p = np.array(p, dtype=np.float32)
        if self.anchor is None:
            self.anchor = p
            return p
        if np.linalg.norm(p - self.anchor) < self.r:
            return self.anchor
        self.anchor = p
        return p


class FixationDetector:
    def __init__(self, radius_px=35, min_time=0.7):
        self.radius = float(radius_px)
        self.min_time = float(min_time)
        self.center = None
        self.t0 = None
        self.is_fixating = False

    def update(self, p, t):
        p = np.array(p, dtype=np.float32)
        if self.center is None:
            self.center = p
            self.t0 = t
            self.is_fixating = False
            return self.is_fixating, 0.0

        if np.linalg.norm(p - self.center) <= self.radius:
            if self.t0 is None:
                self.t0 = t
            dur = t - self.t0
            self.is_fixating = dur >= self.min_time
            return self.is_fixating, dur

        self.center = p
        self.t0 = t
        self.is_fixating = False
        return self.is_fixating, 0.0


# ---------------------------
# Main
# ---------------------------
def main():
    if not HAS_PYAUTOGUI:
        print("Bitte installiere pyautogui (pip install pyautogui), damit Screen-Größe korrekt ist.")
        return

    sw, sh = pyautogui.size()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Konnte Kamera nicht öffnen.")
        return

    # METRICS LOGGER INITIALISIEREN
    logger = MetricsLogger(output_dir="metrics", enabled=True)

    FS_WIN = "Calibration (Fullscreen)"
    CAM_WIN = "Camera Preview"

    cv2.namedWindow(FS_WIN, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(FS_WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    cv2.namedWindow(CAM_WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(CAM_WIN, 560, 320)

    calib_points = make_calib_points_13(sw, sh)
    calib_idx = 0

    mode = "CALIB"  # CALIB / TRACK
    status = "c=start | SPACE=collect | r=recalib | q/ESC=quit"

    collect_seconds = 0.8
    countdown_seconds = 0.8
    min_stable_time = 0.25

    collecting = False
    countdown = False
    t_countdown_start = 0.0
    t_collect_start = 0.0

    calibrator = Calibrator(ridge_lam=1e-2)

    jump_gate = JumpGate(max_step_px=50)
    deadzone = Deadzone(radius_px=3)
    # Etwas längere Dwell-Time für den simulierten Klick (entspricht Kapitel 3.6.3)
    fix = FixationDetector(radius_px=100, min_time=0.80)

    pred_filter = OneEuroFilter(min_cutoff=1.2, beta=0.02, d_cutoff=1.0)
    gate = StabilityGate(window=12)
    stable_start = None

    # Trackings State für Metriken
    last_px, last_py = 0.0, 0.0
    
    # Target Acquisition Test Setup (5 Testziele wie in der Studienarbeit)
    test_targets = [
        (int(sw*0.1), int(sh*0.1)),
        (int(sw*0.9), int(sh*0.1)),
        (int(sw*0.5), int(sh*0.5)),
        (int(sw*0.1), int(sh*0.9)),
        (int(sw*0.9), int(sh*0.9))
    ]
    test_idx = 0

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as face_mesh:

        while True:
            # FRAME START LOGGING
            logger.frame_start()

            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)

            feats_exp = None
            head_ypr = None
            
            px, py = 0.0, 0.0 # Standardwerte, falls Gesicht verloren geht

            if res.multi_face_landmarks:
                lms = res.multi_face_landmarks[0].landmark

                base_feats, debug = gaze_features(lms, w, h)
                head_ypr = estimate_head_pose(lms, w, h)

                if head_ypr is not None:
                    feat_vec = np.concatenate([base_feats, head_ypr], axis=0)
                else:
                    feat_vec = np.concatenate([base_feats, np.zeros(3, dtype=np.float32)], axis=0)

                feats_exp = poly2_expand(feat_vec)

                l_iris, r_iris, l_outer, l_inner, r_inner, r_outer = debug
                for p in [l_outer, l_inner, r_inner, r_outer]:
                    cv2.circle(frame, (int(p[0]), int(p[1])), 2, (0, 255, 0), -1)
                cv2.circle(frame, (int(l_iris[0]), int(l_iris[1])), 3, (255, 0, 0), -1)
                cv2.circle(frame, (int(r_iris[0]), int(r_iris[1])), 3, (255, 0, 0), -1)

                if head_ypr is not None:
                    yaw, pitch, roll = head_ypr
                    cv2.putText(frame, f"Head y/p/r: {yaw:+.2f} {pitch:+.2f} {roll:+.2f}",
                                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2, cv2.LINE_AA)

            canvas = np.zeros((sh, sw, 3), dtype=np.uint8)

            if mode == "CALIB":
                tx, ty = calib_points[calib_idx]
                draw_target(canvas, tx, ty, label=f"{calib_idx+1}/{len(calib_points)}")

                cv2.putText(canvas, "Look at the target",
                            (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(canvas, status,
                            (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (200, 200, 200), 2, cv2.LINE_AA)

                if countdown:
                    elapsed = time.time() - t_countdown_start
                    left = max(0.0, countdown_seconds - elapsed)
                    cv2.putText(canvas, f"Hold steady... {left:.1f}s",
                                (50, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2, cv2.LINE_AA)

                    if feats_exp is not None:
                        gate.push(feats_exp)
                        is_stable = gate.stable(thresh=0.012)
                        if is_stable:
                            if stable_start is None:
                                stable_start = time.time()
                            stable_ok = (time.time() - stable_start) >= min_stable_time
                        else:
                            stable_start = None
                            stable_ok = False

                        cv2.putText(canvas, f"Stable: {'YES' if stable_ok else 'NO'}",
                                    (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                                    (0, 255, 0) if stable_ok else (0, 0, 255), 2, cv2.LINE_AA)
                    else:
                        stable_ok = False
                        stable_start = None

                    if left <= 0.0 and stable_ok:
                        countdown = False
                        collecting = True
                        t_collect_start = time.time()

                if collecting:
                    elapsed = time.time() - t_collect_start
                    left = max(0.0, collect_seconds - elapsed)

                    cv2.putText(canvas, f"Recording... {left:.1f}s",
                                (50, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2, cv2.LINE_AA)

                    if feats_exp is not None:
                        calibrator.add_sample(feats_exp, np.array([tx, ty], dtype=np.float32))

                    if left <= 0.0:
                        collecting = False
                        gate = StabilityGate(window=12)
                        stable_start = None

                        calib_idx += 1
                        if calib_idx >= len(calib_points):
                            ok_fit = calibrator.fit()
                            if ok_fit:
                                mode = "TRACK"
                                status = "TRACKING | r=recalib | q/ESC=quit"
                                test_idx = 0 # Starte Target Test Sequence
                            else:
                                mode = "CALIB"
                                status = "Fit failed. Press c to restart."
                                calib_idx = 0
                                calibrator = Calibrator(ridge_lam=1e-2)

            else:  # TRACK
                cv2.putText(canvas, "Tracking (r=recalib, q/ESC=quit)",
                            (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)

                if feats_exp is not None:
                    now = time.time()
                    pred = calibrator.predict(feats_exp)
                    if pred is not None:
                        pred_f = pred_filter.update(pred, now)
                        pred_g = jump_gate.update(pred_f)
                        is_fix, dur = fix.update(pred_g, now)

                        if is_fix:
                            pred_filter.min_cutoff = 0.35
                            pred_filter.beta = 0.005
                            pred_final = deadzone.update(pred_g)
                        else:
                            pred_filter.min_cutoff = 1.2
                            pred_filter.beta = 0.02
                            deadzone.reset()
                            pred_final = pred_g

                        px, py = float(pred_final[0]), float(pred_final[1])
                        px = clamp(px, 0, sw - 1)
                        py = clamp(py, 0, sh - 1)

                        pyautogui.moveTo(int(px), int(py), duration=0)

                        cv2.putText(canvas, f"Gaze: {int(px)},{int(py)}",
                                    (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2, cv2.LINE_AA)
                        cv2.putText(canvas, f"Fixation: {'YES' if is_fix else 'NO'} {dur:.2f}s",
                                    (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                                    (0,255,0) if is_fix else (200,200,200), 2, cv2.LINE_AA)

                        # --- TARGET ACQUISITION TEST & METRICS ---
                        if test_idx < len(test_targets):
                            tx, ty = test_targets[test_idx]
                            draw_target(canvas, tx, ty, label=f"Target {test_idx+1}/5")

                            # Log target spawn
                            if not logger.has_active_target():
                                logger.target_appeared()

                            # Log Click via Dwell-Time / Fixation near Target
                            dist_to_target = math.hypot(px - tx, py - ty)
                            if is_fix and dist_to_target <= 100: # Innerhalb Akzeptanzradius (vgl. Kap 3.6.3)
                                logger.click_registered(px, py)
                                test_idx += 1
                                # Reset Fixation damit nicht aus Versehen doppelt "geklickt" wird
                                fix.is_fixating = False
                                fix.t0 = None 
                        else:
                            cv2.putText(canvas, "Test abgeschlossen! Metriken gespeichert.",
                                        (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 2, cv2.LINE_AA)

                else:
                    cv2.putText(canvas, "No face detected",
                                (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2, cv2.LINE_AA)

            # Delta Berechnung für die Metriken
            dx = px - last_px if px != 0.0 else 0.0
            dy = py - last_py if py != 0.0 else 0.0
            last_px, last_py = px, py

            # FRAME END LOGGING (Deltas und absolute Koordinaten)
            logger.frame_end(cursor_delta_x=dx, cursor_delta_y=dy, x=pyautogui.position().x, y=pyautogui.position().y)

            cv2.imshow(FS_WIN, canvas)
            cv2.imshow(CAM_WIN, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

            if key == ord('c') or key == ord('r'):
                mode = "CALIB"
                calib_idx = 0
                collecting = False
                countdown = False
                calibrator = Calibrator(ridge_lam=1e-2)
                gate = StabilityGate(window=12)
                stable_start = None
                status = "Calibration / Recalibrating. Press SPACE at each target."

            if key == 32:  # SPACE
                if mode == "CALIB":
                    if feats_exp is None:
                        status = "No face detected. Improve light / face in view."
                    else:
                        countdown = True
                        collecting = False
                        t_countdown_start = time.time()
                        gate = StabilityGate(window=12)
                        stable_start = None
                        status = "Countdown started..."

        # RESOURCES CLEANUP
        logger.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()