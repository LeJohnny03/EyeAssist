import cv2
import numpy as np
import math


# --- FaceMesh landmark indices (MediaPipe) ---
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

# Iris landmarks (requires refine_landmarks=True)
LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

# --- Head pose landmark indices ---
NOSE_TIP = 1
CHIN = 152
MOUTH_LEFT = 61
MOUTH_RIGHT = 291


class EMAFilter:
    def __init__(self, alpha=0.2):
        self.alpha = float(alpha)
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

    l_mid = (l_outer + l_inner) * 0.5
    r_mid = (r_inner + r_outer) * 0.5
    l_y = (l_iris[1] - l_mid[1]) / l_w
    r_y = (r_iris[1] - r_mid[1]) / r_w

    feats = np.array([l_x, l_y, r_x, r_y], dtype=np.float32)
    feats = np.clip(feats, -2.0, 2.0)

    dbg = (l_iris, r_iris, l_outer, l_inner, r_inner, r_outer)
    return feats, dbg


def rotationMatrixToEulerAngles(R):
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
    image_points = np.array([
        lm_to_xy(landmarks, NOSE_TIP, w, h),
        lm_to_xy(landmarks, CHIN, w, h),
        lm_to_xy(landmarks, LEFT_EYE_OUTER, w, h),
        lm_to_xy(landmarks, RIGHT_EYE_OUTER, w, h),
        lm_to_xy(landmarks, MOUTH_LEFT, w, h),
        lm_to_xy(landmarks, MOUTH_RIGHT, w, h),
    ], dtype=np.float32)

    model_points = np.array([
        (0.0,   0.0,    0.0),
        (0.0, -63.0,  -12.0),
        (-43.0, 32.0,  -26.0),
        (43.0,  32.0,  -26.0),
        (-28.0,-28.0,  -24.0),
        (28.0, -28.0,  -24.0),
    ], dtype=np.float32)

    focal_length = float(w)
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

    tz = float(tvec[2])
    tz_norm = tz / (focal_length + 1e-6)

    feats = np.array([yaw, pitch, roll, tz_norm], dtype=np.float32)
    feats = np.clip(feats, -2.0, 2.0)

    return feats, {"rvec": rvec, "tvec": tvec}


def compute_hybrid_features(landmarks, w, h):
    eye_feats, eye_dbg = gaze_features(landmarks, w, h)
    head_feats, head_dbg = head_pose_features(landmarks, w, h)

    if head_feats is not None:
        feats = np.concatenate([eye_feats, head_feats], axis=0)
    else:
        feats = np.concatenate([eye_feats, np.zeros((4,), dtype=np.float32)], axis=0)

    return feats, {"eye_dbg": eye_dbg, "head_dbg": head_dbg}


class Calibrator:
    def __init__(self, ridge_lambda=1e-2):
        self.X = []
        self.Y = []
        self.W = None
        self.lam = float(ridge_lambda)

    def reset(self):
        self.X.clear()
        self.Y.clear()
        self.W = None

    def add_sample(self, feats, screen_xy):
        self.X.append(np.append(feats, 1.0))  # bias
        self.Y.append(screen_xy)

    def fit(self):
        if len(self.X) < 8:
            return False
        X = np.stack(self.X, axis=0).astype(np.float32)
        Y = np.stack(self.Y, axis=0).astype(np.float32)

        A = X.T @ X + self.lam * np.eye(X.shape[1], dtype=np.float32)
        B = X.T @ Y
        self.W = np.linalg.solve(A, B)
        return True

    def predict(self, feats):
        if self.W is None:
            return None
        x = np.append(feats, 1.0).astype(np.float32)
        return x @ self.W


def make_calib_points(sw, sh, margin=0.12):
    xs = [margin, 0.5, 1 - margin]
    ys = [margin, 0.5, 1 - margin]
    pts = []
    for y in ys:
        for x in xs:
            pts.append((int(x * sw), int(y * sh)))
    return pts
