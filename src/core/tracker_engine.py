"""MediaPipe Face Mesh Tracking Engine"""
import cv2
import mediapipe as mp
import numpy as np
from collections import deque

from utils.math_helpers import OneEuroFilter

_FACE_3D_MODEL = np.array([
    [0.0,   0.0,    0.0],
    [0.0,  -63.6, -12.5],
    [-43.3, 32.7, -26.0],
    [43.3,  32.7, -26.0],
    [-28.9,-28.9, -24.1],
    [28.9, -28.9, -24.1],
], dtype=np.float64)

_POSE_LANDMARK_IDS = [1, 199, 33, 263, 61, 291]

_LANDMARK_SMOOTH_SIZE = 5  # Frames für Landmark-Glättung


class TrackerEngine:
    """Verwaltet MediaPipe Face Mesh Tracking"""
    def __init__(self, config):
        self.config = config
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=config.get('tracking.max_num_faces', 1),
            refine_landmarks=config.get('tracking.refine_landmarks', True),
            min_detection_confidence=config.get('tracking.min_detection_confidence', 0.5),
            min_tracking_confidence=config.get('tracking.min_tracking_confidence', 0.5),
            static_image_mode=config.get('tracking.static_image_mode', False)
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.current_landmarks = None

        self._img_w = config.get('camera.width', 640)
        self._img_h = config.get('camera.height', 480)

        # Verbesserte Kameramatrix: focal ≈ 1.2 * Bildbreite
        # (empirisch besser als focal = Bildbreite für typische USB-Webcams)
        focal = float(self._img_w) * 1.2
        cx, cy = self._img_w / 2.0, self._img_h / 2.0
        self._camera_matrix = np.array([
            [focal, 0.0,   cx],
            [0.0,   focal, cy],
            [0.0,   0.0,   1.0]
        ], dtype=np.float64)
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # Puffer für Landmark-Glättung (reduziert solvePnP-Rauschen an der Quelle)
        self._landmark_buffers = {
            idx: deque(maxlen=_LANDMARK_SMOOTH_SIZE)
            for idx in _POSE_LANDMARK_IDS
        }

        # Letzter gültiger Rotationsvektor für ITERATIVE-Initialisierung
        self._prev_rot_vec = None
        self._prev_trans_vec = None
        
        # OneEuroFilter direkt auf Pitch und Yaw – dämpft solvePnP-Rauschen
        # an der Quelle, bevor es in den MouseController gelangt
        pose_mincutoff = config.get('tracking.pose_mincutoff', 1.5)
        pose_beta      = config.get('tracking.pose_beta',      0.05)
        pose_dcutoff   = config.get('tracking.pose_dcutoff',   1.0)
        self._pitch_filter = OneEuroFilter(mincutoff=pose_mincutoff, beta=pose_beta, dcutoff=pose_dcutoff)
        self._yaw_filter   = OneEuroFilter(mincutoff=pose_mincutoff, beta=pose_beta, dcutoff=pose_dcutoff)

        landmark_color = config.get('colors.landmarks', [0, 255, 0])
        self.landmark_drawing_spec = self.mp_drawing.DrawingSpec(
            color=tuple(landmark_color),
            thickness=1
        )

    def _get_smoothed_2d_points(self):
        """Gibt gemittelte 2D-Punkte der PnP-Landmarks zurück."""
        pts = []
        for idx in _POSE_LANDMARK_IDS:
            buf = self._landmark_buffers[idx]
            if len(buf) == 0:
                return None
            mean_x = np.mean([p[0] for p in buf])
            mean_y = np.mean([p[1] for p in buf])
            pts.append([mean_x, mean_y])
        return np.array(pts, dtype=np.float64)

    def _update_landmark_buffers(self):
        """Schreibt aktuelle Landmark-Positionen in die Glättungspuffer."""
        if self.current_landmarks is None:
            return
        for idx in _POSE_LANDMARK_IDS:
            lm = self.current_landmarks[idx]
            self._landmark_buffers[idx].append(
                (lm.x * self._img_w, lm.y * self._img_h)
            )

    def get_head_pose(self):
        """Gibt (pitch, yaw, roll) in Grad zurück oder None.
        
        Verwendet direkt den Rodrigues-Rotationsvektor statt Euler-Winkel,
        um arctan2-Sprünge bei großen Kopfneigungen zu vermeiden.
        """
        if self.current_landmarks is None:
            return None

        pts_2d = np.array([
            [self.current_landmarks[i].x * self._img_w,
            self.current_landmarks[i].y * self._img_h]
            for i in _POSE_LANDMARK_IDS
        ], dtype=np.float64)

        success, rot_vec, _ = cv2.solvePnP(
            _FACE_3D_MODEL, pts_2d,
            self._camera_matrix, self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not success:
            return None

        # Rodrigues-Vektor direkt als Winkelmaß verwenden (in Grad skaliert).
        # rot_vec ist [rx, ry, rz] – Einheit: Radiant.
        # rx ≈ Pitch (Nicken), ry ≈ Yaw (Schütteln), rz ≈ Roll (Kippen)
        # Kein arctan2 → kein Vorzeichensprung bei großen Winkeln.
        pitch_raw = np.degrees(rot_vec[0][0])
        yaw_raw   = np.degrees(rot_vec[2][0])
        roll  = np.degrees(rot_vec[1][0])
        
        # Rauschen direkt auf den Winkelwerten filtern
        pitch = self._pitch_filter.filter(pitch_raw)
        yaw   = self._yaw_filter.filter(yaw_raw)

        return pitch, yaw, roll

    def process_frame(self, frame):
        """Verarbeitet Frame und extrahiert Face Landmarks."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            self.current_landmarks = results.multi_face_landmarks[0].landmark
            return True, results.multi_face_landmarks[0]

        # Filter zurücksetzen bei Gesichtsverlust → kein Stale-Data
        self.current_landmarks = None
        self._pitch_filter.reset()
        self._yaw_filter.reset()
        return False, None

    def get_landmark_position(self, landmark_index):
        """Gibt Position eines spezifischen Landmarks zurück."""
        if self.current_landmarks and 0 <= landmark_index < len(self.current_landmarks):
            landmark = self.current_landmarks[landmark_index]
            return landmark.x, landmark.y, landmark.z
        return None

    def get_nose_tip(self):
        """Gibt Nasenspitzen-Position zurück (Landmark 1)."""
        return self.get_landmark_position(1)

    def get_upper_lip(self):
        """Gibt obere Lippen-Position zurück (Landmark 13)."""
        return self.get_landmark_position(13)

    def get_lower_lip(self):
        """Gibt untere Lippen-Position zurück (Landmark 14)."""
        return self.get_landmark_position(14)

    def draw_landmarks(self, frame, face_landmarks):
        """Zeichnet Face Mesh auf Frame."""
        if face_landmarks:
            self.mp_drawing.draw_landmarks(
                frame,
                face_landmarks,
                self.mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.landmark_drawing_spec
            )

    def close(self):
        """Gibt Ressourcen frei."""
        if self.face_mesh:
            self.face_mesh.close()
