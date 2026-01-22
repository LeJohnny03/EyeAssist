import cv2
import numpy as np
import time
import math

try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = False
except Exception:
    HAS_PYAUTOGUI = False

import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh

# ---------------------------
# MediaPipe landmark indices
# ---------------------------
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

# Landmarks for head pose (2D points) - stable points:
# Nose tip approx: 1
# Chin: 152
# Left eye outer: 33
# Right eye outer: 263
# Left mouth corner: 61
# Right mouth corner: 291
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


# ---------------------------
# One Euro Filter (2D)
# ---------------------------
class OneEuroFilter:
    """
    Adaptive low-pass filter.
    - smooths strongly when signal changes slowly
    - smooths less when signal changes quickly
    """
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
        # alpha = 1 / (1 + tau/dt), tau = 1/(2*pi*cutoff)
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

        # Derivative
        dx = (x - self.x_prev) / max(dt, 1e-6)
        alpha_d = self._alpha(self.d_cutoff, dt)
        dx_hat = self._lowpass(dx, self.dx_prev, alpha_d)
        self.dx_prev = dx_hat

        # Adaptive cutoff
        cutoff = self.min_cutoff + self.beta * float(np.linalg.norm(dx_hat))
        alpha = self._alpha(cutoff, dt)

        x_hat = self._lowpass(x, self.x_prev, alpha)
        self.x_prev = x_hat
        return x_hat


# ---------------------------
# Gaze feature extraction
# ---------------------------
def gaze_features(landmarks, w, h):
    """
    Returns:
      base_feats: [l_x, l_y, r_x, r_y] (normalized iris pos)
      debug points for overlay
    """
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

    # x along eye axis (0 outer -> 1 inner)
    l_x = np.dot((l_iris - l_outer), safe_norm(l_axis)) / l_w
    r_x = np.dot((r_iris - r_inner), safe_norm(r_axis)) / r_w

    # y relative to midpoint, scaled by eye width (rough)
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
    """
    Convert rotation matrix to Euler angles (yaw, pitch, roll) in radians.
    Convention here: approx yaw(Y), pitch(X), roll(Z) depending on decomposition.
    We only need consistent values as extra features.
    """
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6
    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])  # pitch-ish
        y = math.atan2(-R[2, 0], sy)      # yaw-ish
        z = math.atan2(R[1, 0], R[0, 0])  # roll-ish
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0.0
    return np.array([y, x, z], dtype=np.float32)  # [yaw, pitch, roll]

def estimate_head_pose(landmarks, w, h):
    """
    Returns (yaw, pitch, roll) in radians, or None if solvePnP fails.
    Uses a simple generic 3D face model (in arbitrary units).
    """
    image_points = np.array([
        lm_to_xy(landmarks, HP_NOSE, w, h),
        lm_to_xy(landmarks, HP_CHIN, w, h),
        lm_to_xy(landmarks, HP_LEYE, w, h),
        lm_to_xy(landmarks, HP_REYE, w, h),
        lm_to_xy(landmarks, HP_LMOUTH, w, h),
        lm_to_xy(landmarks, HP_RMOUTH, w, h),
    ], dtype=np.float32)

    # Generic 3D model points (rough, unit scale)
    model_points = np.array([
        [0.0,   0.0,   0.0],    # nose tip
        [0.0, -63.0, -12.0],    # chin
        [-43.0, 32.0, -26.0],   # left eye outer
        [43.0,  32.0, -26.0],   # right eye outer
        [-28.0, -28.0, -24.0],  # left mouth
        [28.0,  -28.0, -24.0],  # right mouth
    ], dtype=np.float32)

    focal_length = w  # rough
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
    ypr = rotation_matrix_to_euler(R)  # [yaw, pitch, roll]
    # clip a bit to avoid crazy spikes
    ypr = np.clip(ypr, -1.2, 1.2)
    return ypr


# ---------------------------
# Polynomial feature expansion (degree 2)
# ---------------------------
def poly2_expand(x):
    """
    x: (D,) -> expanded features:
      [x1..xD, x1^2..xD^2, x1*x2, x1*x3, ...]
    """
    x = np.asarray(x, dtype=np.float32)
    D = x.shape[0]
    feats = [x]
    feats.append(x * x)
    # pairwise products
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
        # feats is already expanded (poly2)
        self.X.append(np.append(feats, 1.0))  # bias
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
    # 3x3 grid + 4 edge midpoints = 13
    xs = [margin, 0.5, 1 - margin]
    ys = [margin, 0.5, 1 - margin]
    pts = []
    for y in ys:
        for x in xs:
            pts.append((int(x * sw), int(y * sh)))

    # edge midpoints (top, bottom, left, right)
    pts.append((int(0.5 * sw), int(margin * sh)))
    pts.append((int(0.5 * sw), int((1 - margin) * sh)))
    pts.append((int(margin * sw), int(0.5 * sh)))
    pts.append((int((1 - margin) * sw), int(0.5 * sh)))

    # remove duplicates if any
    uniq = []
    seen = set()
    for p in pts:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    return uniq  # should be 13


def draw_target(canvas, x, y, label=None):
    cv2.circle(canvas, (int(x), int(y)), 30, (0, 255, 255), 3)
    cv2.circle(canvas, (int(x), int(y)), 6, (0, 255, 255), -1)
    if label:
        cv2.putText(canvas, label, (int(x) + 38, int(y) - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)


# ---------------------------
# Calibration quality checks
# ---------------------------
class StabilityGate:
    """
    Keeps a short window of recent feature vectors and checks
    if they're stable enough (low variance).
    """
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
        # mean std across dimensions
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

        # clamp movement instead of freezing
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
    """
    Detects if gaze is stable inside a radius for a minimum duration.
    Useful for dwell-click or for switching into 'steady' smoothing.
    """
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
            # still inside fixation area
            if self.t0 is None:
                self.t0 = t
            dur = t - self.t0
            self.is_fixating = dur >= self.min_time
            return self.is_fixating, dur

        # moved out -> reset fixation
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

    # calibration parameters
    collect_seconds = 0.8     # record duration per target
    countdown_seconds = 0.8   # wait before recording (user settles gaze)
    min_stable_time = 0.25    # must be stable for at least this time before recording

    collecting = False
    countdown = False
    t_countdown_start = 0.0
    t_collect_start = 0.0

    calibrator = Calibrator(ridge_lam=1e-2)

    # Filters
    jump_gate = JumpGate(max_step_px=50)
    deadzone = Deadzone(radius_px=3)
    fix = FixationDetector(radius_px=35, min_time=0.80)

    pred_filter = OneEuroFilter(min_cutoff=1.2, beta=0.02, d_cutoff=1.0)
    was_fix = False


    # optional: separate filter settings if fixating
    pred_filter_fast = OneEuroFilter(min_cutoff=1.3, beta=0.02, d_cutoff=1.0)
    pred_filter_steady = OneEuroFilter(min_cutoff=0.4, beta=0.005, d_cutoff=1.0)



    # Stability gate for calibration (on expanded features)
    gate = StabilityGate(window=12)
    stable_start = None

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as face_mesh:

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)

            feats_exp = None
            head_ypr = None

            if res.multi_face_landmarks:
                lms = res.multi_face_landmarks[0].landmark

                base_feats, debug = gaze_features(lms, w, h)
                head_ypr = estimate_head_pose(lms, w, h)

                if head_ypr is not None:
                    # Combine base gaze features + head pose
                    feat_vec = np.concatenate([base_feats, head_ypr], axis=0)  # D=7
                else:
                    feat_vec = np.concatenate([base_feats, np.zeros(3, dtype=np.float32)], axis=0)

                # Polynomial expansion degree 2
                feats_exp = poly2_expand(feat_vec)

                # Debug overlay on camera preview
                l_iris, r_iris, l_outer, l_inner, r_inner, r_outer = debug
                for p in [l_outer, l_inner, r_inner, r_outer]:
                    cv2.circle(frame, (int(p[0]), int(p[1])), 2, (0, 255, 0), -1)
                cv2.circle(frame, (int(l_iris[0]), int(l_iris[1])), 3, (255, 0, 0), -1)
                cv2.circle(frame, (int(r_iris[0]), int(r_iris[1])), 3, (255, 0, 0), -1)

                if head_ypr is not None:
                    yaw, pitch, roll = head_ypr
                    cv2.putText(frame, f"Head y/p/r: {yaw:+.2f} {pitch:+.2f} {roll:+.2f}",
                                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2, cv2.LINE_AA)

            # Fullscreen canvas
            canvas = np.zeros((sh, sw, 3), dtype=np.uint8)

            if mode == "CALIB":
                tx, ty = calib_points[calib_idx]
                draw_target(canvas, tx, ty, label=f"{calib_idx+1}/{len(calib_points)}")

                cv2.putText(canvas, "Look at the target",
                            (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(canvas, status,
                            (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (200, 200, 200), 2, cv2.LINE_AA)

                # if user hit SPACE -> start countdown
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

                    # only proceed to collecting after countdown AND stability
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
                        # 1) OneEuro (normal)
                        # if we just switched fix/non-fix last frame, optionally reset deadzone anchor
                        pred_f = pred_filter.update(pred, now)

                        # 2) Clamp big jumps (never freeze!)
                        pred_g = jump_gate.update(pred_f)

                        # 3) Fixation detection on gated (NOT deadzoned)
                        is_fix, dur = fix.update(pred_g, now)

                        # 4) If fixating -> stronger smoothing + deadzone
                        if is_fix:
                            pred_filter.min_cutoff = 0.35
                            pred_filter.beta = 0.005
                            #pred_s = pred_filter.update(pred_g, now)  # second pass is OK ONLY if dt>0 normally
                            pred_final = deadzone.update(pred_g)
                        else:
                            pred_filter.min_cutoff = 1.2
                            pred_filter.beta = 0.02
                            deadzone.reset()  # don't let anchor hold you back when moving
                            pred_final = pred_g

                        px, py = float(pred_final[0]), float(pred_final[1])
                        px = clamp(px, 0, sw - 1)
                        py = clamp(py, 0, sh - 1)
                        #pred = pred_filter.update(pred, now)
                        #px, py = float(pred[0]), float(pred[1])
                        #px = clamp(px, 0, sw - 1)
                        #py = clamp(py, 0, sh - 1)

                        # draw predicted gaze
                        #cv2.circle(canvas, (int(px), int(py)), 18, (0, 0, 255), 3)
                        #cv2.circle(canvas, (int(px), int(py)), 4, (0, 0, 255), -1)

                        # move mouse
                        pyautogui.moveTo(int(px), int(py), duration=0)

                        cv2.putText(canvas, f"Gaze: {int(px)},{int(py)}",
                                    (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2, cv2.LINE_AA)
                        cv2.putText(canvas, f"Fixation: {'YES' if is_fix else 'NO'} {dur:.2f}s",
                                    (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                                    (0,255,0) if is_fix else (200,200,200), 2, cv2.LINE_AA)

                else:
                    cv2.putText(canvas, "No face detected",
                                (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2, cv2.LINE_AA)

            # show both windows
            cv2.imshow(FS_WIN, canvas)
            cv2.imshow(CAM_WIN, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                break

            if key == ord('c'):
                mode = "CALIB"
                calib_idx = 0
                collecting = False
                countdown = False
                calibrator = Calibrator(ridge_lam=1e-2)
                gate = StabilityGate(window=12)
                stable_start = None
                status = "Calibration started. Press SPACE at each target."

            if key == ord('r'):
                mode = "CALIB"
                calib_idx = 0
                collecting = False
                countdown = False
                calibrator = Calibrator(ridge_lam=1e-2)
                gate = StabilityGate(window=12)
                stable_start = None
                status = "Recalibrating. Press SPACE at each target."

            if key == 32:  # SPACE
                if mode == "CALIB":
                    if feats_exp is None:
                        status = "No face detected. Improve light / face in view."
                    else:
                        # start countdown before recording
                        countdown = True
                        collecting = False
                        t_countdown_start = time.time()
                        gate = StabilityGate(window=12)
                        stable_start = None
                        status = "Countdown started..."

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
