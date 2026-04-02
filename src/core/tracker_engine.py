"""MediaPipe Face Mesh Tracking Engine"""
import math

import cv2
import mediapipe as mp

class TrackerEngine:
    """Verwaltet MediaPipe Face Mesh Tracking"""

    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473
    LEFT_EYE_INNER   = 133
    LEFT_EYE_OUTER   = 33
    RIGHT_EYE_INNER  = 362
    RIGHT_EYE_OUTER  = 263
    
    # Mundwinkel für Breite des Mundes
    MOUTH_LEFT  = 61
    MOUTH_RIGHT = 291
    
    # Obere/Untere Lippenkontur für Puckered-Erkennung
    UPPER_LIP_TOP    = 0    # Mitte Oberlippe außen
    LOWER_LIP_BOTTOM = 17   # Mitte Unterlippe außen

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
    
    def get_mouth_corners(self):
        """Gibt linken und rechten Mundwinkel zurück"""
        left  = self.get_landmark_position(self.MOUTH_LEFT)
        right = self.get_landmark_position(self.MOUTH_RIGHT)
        return left, right
    
    def get_mouth_width(self):
        """
        Gibt die normalisierte Mundbreite zurück.
        Bei normalem Mund ~0.04–0.06, bei gespitzten Lippen deutlich kleiner.
        """
        left, right = self.get_mouth_corners()
        if left is None or right is None:
            return None
        return abs(right[0] - left[0])
    
    def get_eye_roll_angle(self):
        """
        Berechnet den Roll-Winkel (echte Kopfneigung) aus der Verbindungslinie
        beider äußerer Augenwinkel. Gibt Winkel in Grad zurück.
        Positiv = Kopf nach rechts geneigt, Negativ = nach links geneigt.
        """
        left_outer  = self.get_landmark_position(self.LEFT_EYE_OUTER)
        right_outer = self.get_landmark_position(self.RIGHT_EYE_OUTER)
        if left_outer is None or right_outer is None:
            return 0.0
        dx = right_outer[0] - left_outer[0]
        dy = right_outer[1] - left_outer[1]
        angle_rad = math.atan2(dy, dx)
        return math.degrees(angle_rad)

    def get_iris_delta(self):
        """
        Gibt die Iris-Abweichung relativ zum jeweiligen Augenmittelpunkt zurück.
        Liefert kleine Werte (~0.01–0.03) – nur für Feinjustierung geeignet.
        Gibt (0.0, 0.0) zurück wenn Iris-Landmarks nicht verfügbar sind.
        Benötigt refine_landmarks=True in der Config.
        """
        left_iris  = self.get_landmark_position(self.LEFT_IRIS_CENTER)
        right_iris = self.get_landmark_position(self.RIGHT_IRIS_CENTER)
        l_inner    = self.get_landmark_position(self.LEFT_EYE_INNER)
        l_outer    = self.get_landmark_position(self.LEFT_EYE_OUTER)
        r_inner    = self.get_landmark_position(self.RIGHT_EYE_INNER)
        r_outer    = self.get_landmark_position(self.RIGHT_EYE_OUTER)

        if not all([left_iris, right_iris, l_inner, l_outer, r_inner, r_outer]):
            return 0.0, 0.0

        l_center_x = (l_inner[0] + l_outer[0]) / 2
        l_center_y = (l_inner[1] + l_outer[1]) / 2
        r_center_x = (r_inner[0] + r_outer[0]) / 2
        r_center_y = (r_inner[1] + r_outer[1]) / 2

        delta_x = ((left_iris[0] - l_center_x) + (right_iris[0] - r_center_x)) / 2
        delta_y = ((left_iris[1] - l_center_y) + (right_iris[1] - r_center_y)) / 2
        return delta_x, delta_y

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
