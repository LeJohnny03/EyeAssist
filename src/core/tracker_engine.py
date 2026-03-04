"""MediaPipe Face Mesh Tracking Engine"""
import cv2
import mediapipe as mp
import numpy as np

# Generisches 3D-Gesichtsmodell (in mm, kamerazentriert)
_FACE_3D_MODEL = np.array([
    [0.0, 0.0, 0.0],          # 0: Nasenspitze
    [0.0,   -63.6, -12.5],    # Kinn            (199)
    [-43.3,  32.7, -26.0],    # Linke Augenecke (33)
    [43.3,   32.7, -26.0],    # Rechte Augenecke(263)
    [-28.9, -28.9, -24.1],    # Linker Mundwinkel(61)
    [28.9,  -28.9, -24.1],    # Rechter Mundwinkel(291)
], dtype=np.float64)

_POSE_LANDMARK_IDS = [1, 199, 33, 263, 61, 291]

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

        # Kameramatrix (Näherung ohne physische Kalibrierung)
        focal = float(self._img_w)
        cx, cy = self._img_w / 2.0, self._img_h / 2.0
        self._camera_matrix = np.array([
            [focal, 0.0,   cx ],
            [0.0,   focal, cy ],
            [0.0,   0.0,   1.0]
        ], dtype=np.float64)
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        landmark_color = config.get('colors.landmarks', [0, 255, 0])
        self.landmark_drawing_spec = self.mp_drawing.DrawingSpec(
            color=tuple(landmark_color),
            thickness=1
        )
        
    def get_head_pose(self):
        """Gibt (pitch, yaw, roll) in Grad zurück oder None"""
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

        rot_mat, _ = cv2.Rodrigues(rot_vec)

        # Stabile ZYX-Zerlegung mit Gimbal-Lock-Absicherung
        sy = np.sqrt(rot_mat[0][0] ** 2 + rot_mat[1][0] ** 2)
        if sy > 1e-6:
            pitch = np.degrees(np.arctan2( rot_mat[2][1],  rot_mat[2][2]))
            yaw   = np.degrees(np.arctan2(-rot_mat[2][0],  sy))
            roll  = np.degrees(np.arctan2( rot_mat[1][0],  rot_mat[0][0]))
        else:
            # Gimbal Lock – Roll wird 0 gesetzt, Pitch bleibt stabil
            pitch = np.degrees(np.arctan2(-rot_mat[1][2],  rot_mat[1][1]))
            yaw   = np.degrees(np.arctan2(-rot_mat[2][0],  sy))
            roll  = 0.0

        # Yaw negieren: kompensiert flip_horizontal der Kamera
        #yaw = -yaw

        return pitch, yaw, roll

    def process_frame(self, frame):
        """Verarbeitet Frame und extrahiert Face Landmarks"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            self.current_landmarks = results.multi_face_landmarks[0].landmark
            return True, results.multi_face_landmarks[0]

        self.current_landmarks = None
        return False, None

    def get_landmark_position(self, landmark_index):
        """Gibt Position eines spezifischen Landmarks zurück"""
        if self.current_landmarks and 0 <= landmark_index < len(self.current_landmarks):
            landmark = self.current_landmarks[landmark_index]
            return landmark.x, landmark.y, landmark.z
        return None

    def get_nose_tip(self):
        """Gibt Nasenspitzen-Position zurück (Landmark 1)"""
        return self.get_landmark_position(1)

    def get_upper_lip(self):
        """Gibt obere Lippen-Position zurück (Landmark 13)"""
        return self.get_landmark_position(13)

    def get_lower_lip(self):
        """Gibt untere Lippen-Position zurück (Landmark 14)"""
        return self.get_landmark_position(14)

    def draw_landmarks(self, frame, face_landmarks):
        """Zeichnet Face Mesh auf Frame"""
        if face_landmarks:
            self.mp_drawing.draw_landmarks(
                frame,
                face_landmarks,
                self.mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.landmark_drawing_spec
            )

    def close(self):
        """Gibt Ressourcen frei"""
        if self.face_mesh:
            self.face_mesh.close()