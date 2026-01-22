import cv2
import numpy as np
import time
import math

# Optional mouse control
try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = False
except Exception:
    HAS_PYAUTOGUI = False

import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

# --- FaceMesh landmark indices (MediaPipe) ---
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

# Iris landmarks (requires refine_landmarks=True)
LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

# --- Head pose landmark indices (commonly used & stable) ---
NOSE_TIP = 1
CHIN = 152
MOUTH_LEFT = 61
MOUTH_RIGHT = 291
# reuse LEFT_EYE_OUTER = 33, RIGHT_EYE_OUTER = 263


class EMAFilter:
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.state = None

    def update(self, value):
        value = np.array(value, dtype=np.float32)
        if self.state is None:
            self.state = value
        else:
            self.state = self.alpha * value + (1 - self.alpha) * self.state
        return self.state


def lm_to_xy(landmarks, idx, w, h):
    lm = landmarks[idx]
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def iris_center(landmarks, indices, w, h):
    pts = np.stack([lm_to_xy(landmarks, i, w, h) for i in indices], axis=0)
    return pts.mean(axis=0)


def safe_norm(v, eps=1e-6):
    n = np.linalg.norm(v)
    return v / (n + eps)


def gaze_features(landmarks, w, h):
    # Eye corners
    l_outer = lm_to_xy(landmarks, LEFT_EYE_OUTER, w, h)
    l_inner = lm_to_xy(landmarks, LEFT_EYE_INNER, w, h)
    r_inner = lm_to_xy(landmarks, RIGHT_EYE_INNER, w, h)
    r_outer = lm_to_xy(landmarks, RIGHT_EYE_OUTER, w, h)

    # Iris centers
    l_iris = iris_center(landmarks, LEFT_IRIS, w, h)
    r_iris = iris_center(landmarks, RIGHT_IRIS, w, h)

    # Axes
    l_axis = (l_inner - l_outer)
    r_axis = (r_outer - r_inner)

    l_w = np.linalg.norm(l_axis) + 1e-6
    r_w = np.linalg.norm(r_axis) + 1e-6

    # x along eye axis (0 at outer, 1 at inner)
    l_x = np.dot((l_iris - l_outer), safe_norm(l_axis)) / l_w
    r_x = np.dot((r_iris - r_inner), safe_norm(r_axis)) / r_w

    # y relative to mid, scaled by eye width
    l_mid = (l_outer + l_inner) * 0.5
    r_mid = (r_inner + r_outer) * 0.5
    l_y = (l_iris[1] - l_mid[1]) / l_w
    r_y = (r_iris[1] - r_mid[1]) / r_w

    feats = np.array([l_x, l_y, r_x, r_y], dtype=np.float32)
    feats = np.clip(feats, -2.0, 2.0)
    return feats, (l_iris, r_iris, l_outer, l_inner, r_inner, r_outer)

def rotationMatrixToEulerAngles(R):
    # Returns yaw, pitch, roll in radians (approx, OpenCV-style)
    # yaw: y-axis, pitch: x-axis, roll: z-axis (convention varies; debug overlay helps)
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6

    if not singular:
        pitch = math.atan2(R[2, 1], R[2, 2])
        yaw = math.atan2(-R[2, 0], sy)
        roll = math.atan2(R[1, 0], R[0, 0])
    else:
        pitch = math.atan2(-R[1, 2], R[1, 1])
        yaw = math.atan2(-R[2, 0], sy)
        roll = 0

    return yaw, pitch, roll

def head_pose_features(landmarks, w, h):
    """
    Estimate head pose via solvePnP.
    Returns:
      feats: [yaw, pitch, roll, tz_norm] (tz normalized)
      dbg: dict with rvec, tvec, nose_2d, axis_2d (for drawing)
    """
    # 2D image points from landmarks
    image_points = np.array([
        lm_to_xy(landmarks, NOSE_TIP, w, h),       # Nose tip
        lm_to_xy(landmarks, CHIN, w, h),           # Chin
        lm_to_xy(landmarks, LEFT_EYE_OUTER, w, h), # Left eye outer corner
        lm_to_xy(landmarks, RIGHT_EYE_OUTER, w, h),# Right eye outer corner
        lm_to_xy(landmarks, MOUTH_LEFT, w, h),     # Left mouth corner
        lm_to_xy(landmarks, MOUTH_RIGHT, w, h),    # Right mouth corner
    ], dtype=np.float32)

    # Generic 3D model points (rough face model in mm)
    # Not person-specific, but good enough for relative pose stability.
    model_points = np.array([
        (0.0,   0.0,    0.0),     # Nose tip
        (0.0, -63.0,  -12.0),     # Chin
        (-43.0, 32.0,  -26.0),    # Left eye outer
        (43.0,  32.0,  -26.0),    # Right eye outer
        (-28.0,-28.0,  -24.0),    # Left mouth corner
        (28.0, -28.0,  -24.0),    # Right mouth corner
    ], dtype=np.float32)

    # Camera intrinsics (approx)
    focal_length = float(w)  # simple approximation
    center = (w / 2.0, h / 2.0)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float32)

    dist_coeffs = np.zeros((4, 1), dtype=np.float32)

    ok, rvec, tvec = cv2.solvePnP(
        model_points,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not ok:
        return None, None

    R, _ = cv2.Rodrigues(rvec)
    yaw, pitch, roll = rotationMatrixToEulerAngles(R)

    # tz: distance-ish; normalize by focal length so it is scale-consistent-ish
    tz = float(tvec[2])
    tz_norm = tz / (focal_length + 1e-6)

    # Project small axis for debug drawing (in model space)
    axis_len = 40.0
    axis_3d = np.array([
        (0, 0, 0),
        (axis_len, 0, 0),
        (0, axis_len, 0),
        (0, 0, axis_len),
    ], dtype=np.float32)
    axis_2d, _ = cv2.projectPoints(axis_3d, rvec, tvec, camera_matrix, dist_coeffs)
    axis_2d = axis_2d.reshape(-1, 2)

    feats = np.array([yaw, pitch, roll, tz_norm], dtype=np.float32)
    feats = np.clip(feats, -2.0, 2.0)

    dbg = {
        "rvec": rvec,
        "tvec": tvec,
        "nose_2d": image_points[0],
        "axis_2d": axis_2d
    }
    return feats, dbg

class Calibrator:
    def __init__(self):
        self.X = []
        self.Y = []
        self.W = None

    def add_sample(self, feats, screen_xy):
        self.X.append(np.append(feats, 1.0))  # bias
        self.Y.append(screen_xy)

    def fit(self):
        if len(self.X) < 8:
            return False
        X = np.stack(self.X, axis=0)
        Y = np.stack(self.Y, axis=0)

        lam = 1e-2
        A = X.T @ X + lam * np.eye(X.shape[1], dtype=np.float32)
        B = X.T @ Y
        self.W = np.linalg.solve(A, B)
        return True

    def predict(self, feats):
        if self.W is None:
            return None
        x = np.append(feats, 1.0)
        return x @ self.W


def make_calib_points(sw, sh, margin=0.12):
    xs = [margin, 0.5, 1 - margin]
    ys = [margin, 0.5, 1 - margin]
    pts = []
    for y in ys:
        for x in xs:
            pts.append((int(x * sw), int(y * sh)))
    return pts


def draw_target(canvas, x, y, label=None):
    cv2.circle(canvas, (int(x), int(y)), 28, (0, 255, 255), 3)
    cv2.circle(canvas, (int(x), int(y)), 5, (0, 255, 255), -1)
    if label:
        cv2.putText(canvas, label, (int(x) + 35, int(y) - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

def draw_face_crosshair(frame, nose_xy, axis_2d):
    """
    Draw a crosshair on nose position + projected axes
    axis_2d: [origin, x_end, y_end, z_end] in 2D
    """
    x, y = int(nose_xy[0]), int(nose_xy[1])

    # Crosshair
    cv2.drawMarker(frame, (x, y), (0, 255, 255), markerType=cv2.MARKER_CROSS,
                   markerSize=24, thickness=2)

    # Axes
    o = axis_2d[0]
    x_end = axis_2d[1]
    y_end = axis_2d[2]
    z_end = axis_2d[3]

    o = (int(o[0]), int(o[1]))
    x_end = (int(x_end[0]), int(x_end[1]))
    y_end = (int(y_end[0]), int(y_end[1]))
    z_end = (int(z_end[0]), int(z_end[1]))

    cv2.line(frame, o, x_end, (0, 0, 255), 2)   # X (red)
    cv2.line(frame, o, y_end, (0, 255, 0), 2)   # Y (green)
    cv2.line(frame, o, z_end, (255, 0, 0), 2)   # Z (blue)

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Konnte Kamera nicht öffnen.")
        return

    # Determine screen size (best via pyautogui)
    if HAS_PYAUTOGUI:
        sw, sh = pyautogui.size()
    else:
        # Fallback values (may be wrong)
        sw, sh = 1920, 1080
        print("WARN: pyautogui nicht installiert -> Screen-Size fallback auf 1920x1080.")

    # Windows setup
    FS_WIN = "Calibration (Fullscreen)"
    CAM_WIN = "Camera Preview"

    cv2.namedWindow(FS_WIN, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(FS_WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    cv2.namedWindow(CAM_WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(CAM_WIN, 520, 300)

    calib_points = make_calib_points(sw, sh)
    calib_idx = 0
    collecting = False
    collected = 0
    collect_n = 30  # samples per point
    last_collect_time = 0.0

    calibrator = Calibrator()
    feat_filter = EMAFilter(alpha=0.25)
    pred_filter = EMAFilter(alpha=0.20)

    mode = "CALIB"
    status = "c=start calib | SPACE=capture | r=recalib | q=quit"

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)

            feats = None
            if res.multi_face_landmarks:
                lms = res.multi_face_landmarks[0].landmark
                
                eye_feats, eye_dbg = gaze_features(lms, w, h)
                head_feats, head_dbg = head_pose_features(lms, w, h)
                
                ##feats, debug = gaze_features(lms, w, h)
                #feats = feat_filter.update(feats)

                # debug points on camera & draw iris/corners debug
                l_iris, r_iris, l_outer, l_inner, r_inner, r_outer = eye_dbg
                for p in [l_outer, l_inner, r_inner, r_outer]:
                    cv2.circle(frame, (int(p[0]), int(p[1])), 2, (0, 255, 0), -1)
                cv2.circle(frame, (int(l_iris[0]), int(l_iris[1])), 3, (255, 0, 0), -1)
                cv2.circle(frame, (int(r_iris[0]), int(r_iris[1])), 3, (255, 0, 0), -1)

                # Draw head pose crosshair + axes if available
                if head_feats is not None and head_dbg is not None:
                    draw_face_crosshair(frame, head_dbg["nose_2d"], head_dbg["axis_2d"])
                    
                    yaw, pitch, roll, tz_norm = head_feats
                    cv2.putText(frame, f"Head yaw/pitch/roll: {yaw:+.2f} {pitch:+.2f} {roll:+.2f}",
                                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(frame, f"Head tz_norm: {tz_norm:+.3f}",
                                (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (255, 255, 255), 2, cv2.LINE_AA)
                    
                # Hybrid features vector (eyes + headpose)
                if head_feats is not None:
                    feats = np.concatenate([eye_feats, head_feats], axis=0)
                else:
                    # Fallback if solvePnp fails
                    feats = np.concatenate([eye_feats, np.zeros((4,), dtype=np.float32)], axis=0)
                    
                feats = feat_filter.update(feats)
                
            # --- Fullscreen canvas ---
            canvas = np.zeros((sh, sw, 3), dtype=np.uint8)

            if mode == "CALIB":
                tx, ty = calib_points[calib_idx]
                draw_target(canvas, tx, ty, label=f"{calib_idx+1}/9")

                # Help text
                cv2.putText(canvas, "Look at the target, then press SPACE",
                            (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(canvas, status,
                            (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2, cv2.LINE_AA)

                if collecting and feats is not None:
                    now = time.time()
                    if now - last_collect_time > 0.01:
                        calibrator.add_sample(feats, np.array([tx, ty], dtype=np.float32))
                        collected += 1
                        last_collect_time = now

                    cv2.putText(canvas, f"Collecting {collected}/{collect_n}",
                                (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2, cv2.LINE_AA)

                    if collected >= collect_n:
                        collecting = False
                        collected = 0
                        calib_idx += 1

                        if calib_idx >= len(calib_points):
                            ok_fit = calibrator.fit()
                            if ok_fit:
                                mode = "TRACK"
                                status = "TRACKING | r=recalib | q=quit"
                            else:
                                mode = "CALIB"
                                status = "Fit failed. Press c to restart."
                                calib_idx = 0
                                calibrator = Calibrator()

            else:  # TRACK
                cv2.putText(canvas, "Tracking (press r to recalibrate, q to quit)",
                            (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

                if feats is not None:
                    pred = calibrator.predict(feats)
                    if pred is not None:
                        pred = pred_filter.update(pred)
                        px, py = float(pred[0]), float(pred[1])
                        px = max(0, min(sw - 1, px))
                        py = max(0, min(sh - 1, py))

                        # draw predicted point in fullscreen
                        cv2.circle(canvas, (int(px), int(py)), 18, (0, 0, 255), 3)
                        cv2.circle(canvas, (int(px), int(py)), 4, (0, 0, 255), -1)

                        if HAS_PYAUTOGUI:
                            pyautogui.moveTo(int(px), int(py), duration=0)

                        cv2.putText(canvas, f"Gaze: {int(px)},{int(py)}",
                                    (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(canvas, "No face detected",
                                (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)

            # show windows
            cv2.imshow(FS_WIN, canvas)
            cv2.imshow(CAM_WIN, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                break

            if key == ord('c'):
                mode = "CALIB"
                calib_idx = 0
                collecting = False
                collected = 0
                calibrator = Calibrator()
                status = "Calibration started. Look at target, press SPACE to capture."

            if key == ord('r'):
                mode = "CALIB"
                calib_idx = 0
                collecting = False
                collected = 0
                calibrator = Calibrator()
                status = "Recalibrating. Look at target, press SPACE to capture."

            if key == 32:  # SPACE
                if mode == "CALIB":
                    if feats is None:
                        status = "No face detected. Ensure light & face visible."
                    else:
                        collecting = True
                        collected = 0
                        last_collect_time = 0.0
                        status = "Collecting... keep gaze steady."

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
