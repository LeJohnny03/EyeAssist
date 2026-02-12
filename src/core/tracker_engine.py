"""MediaPipe Face Mesh Tracking Engine"""
import cv2
import mediapipe as mp

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

        # Farbe für Landmarks aus Config
        landmark_color = config.get('colors.landmarks', [0, 255, 0])
        self.landmark_drawing_spec = self.mp_drawing.DrawingSpec(
            color=tuple(landmark_color), 
            thickness=1
        )

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