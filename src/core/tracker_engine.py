"""MediaPipe Face Mesh Tracking Engine"""
import cv2
import numpy as np
import mediapipe as mp

class TrackerEngine:
    """Verwaltet MediaPipe Face Mesh Tracking"""

    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473
    LEFT_EYE_INNER   = 133
    LEFT_EYE_OUTER   = 33
    RIGHT_EYE_INNER  = 362
    RIGHT_EYE_OUTER  = 263
    
    # Augen-Kontur (für EAR)
    # Linkes Auge: oben/unten je 2 Punkte, links/rechts je 1 Punkt
    LEFT_EYE  = [33, 160, 158, 133, 153, 144]   # p1..p6 im Uhrzeigersinn
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]
    
    # Lippen (präziser als vorher)
    UPPER_LIP_TOP    = 13    # Mitte oben
    LOWER_LIP_BOTTOM = 14    # Mitte unten
    UPPER_LIP_CENTER = 0     # Äußerer Mittelpunkt
    MOUTH_LEFT       = 61
    MOUTH_RIGHT      = 291
    MOUTH_TOP        = 37    # Für Kussmund-Breite
    MOUTH_BOTTOM     = 267
    
    # Augenbrauen
    LEFT_BROW_TOP  = 105
    LEFT_EYE_TOP_L = 159
    RIGHT_BROW_TOP = 334
    RIGHT_EYE_TOP_R= 386

    # Nasenspitze
    NOSE_TIP = 1
    

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
        return self.get_landmark_position(self.NOSE_TIP)

    def get_upper_lip(self):
        """Gibt obere Lippen-Position zurück (Landmark 13)"""
        return self.get_landmark_position(self.UPPER_LIP_TOP)

    def get_lower_lip(self):
        """Gibt untere Lippen-Position zurück (Landmark 14)"""
        return self.get_landmark_position(self.LOWER_LIP_BOTTOM)

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
    
    def get_eye_aspect_ratio(self, eye_indices):
        """
        Eye Aspect Ratio (EAR) nach Soukupova & Cech.
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        Wert ~0.25–0.30 bei offenen Augen, < threshold bei Schluss.
        """
        pts = [self.get_landmark_position(i) for i in eye_indices]
        if any(p is None for p in pts):
            return 1.0  # Fehler → als offen werten

        p = [np.array(pt[:2]) for pt in pts]
        ear = (np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])) / \
              (2.0 * np.linalg.norm(p[0] - p[3]) + 1e-6)
        return float(ear)
    
    def get_left_ear(self):
        """EAR des linken Auges (< ~0.20 = geschlossen)."""
        return self.get_eye_aspect_ratio(self.LEFT_EYE)
    
    def get_right_ear(self):
        """EAR des rechten Auges."""
        return self.get_eye_aspect_ratio(self.RIGHT_EYE)
    
    def get_mouth_metrics(self):
        """
        Gibt ein dict mit Mundmetriken zurück:
          - 'open'  : vertikale Öffnung (normiert auf Gesichtsbreite)
          - 'width' : horizontale Breite
          - 'ratio' : Höhe/Breite (hoch bei Kussmund)
        """
        top    = self.get_landmark_position(self.UPPER_LIP_TOP)
        bottom = self.get_landmark_position(self.LOWER_LIP_BOTTOM)
        left   = self.get_landmark_position(self.MOUTH_LEFT)
        right  = self.get_landmark_position(self.MOUTH_RIGHT)

        if not all([top, bottom, left, right]):
            return {"open": 0.0, "width": 0.0, "ratio": 0.0}

        opening = abs(top[1] - bottom[1])
        width   = abs(left[0] - right[0]) + 1e-6
        return {
            "open":  opening,
            "width": width,
            "ratio": opening / width,   # Kussmund: Breite klein → ratio hoch
        }
        
    def get_smile_metric(self):
        """
        Verbesserte Smile-Erkennung:
        Misst die horizontale Ausdehnung des Mundes relativ zur Gesichtsbreite
        (Lächeln → Mundwinkel nach außen → größere Breite).
        Gibt normierte Breite zurück.
        Zusätzlich: Asymmetrie-Check gegen falsches Triggern.
        """
        left  = self.get_landmark_position(self.MOUTH_LEFT)
        right = self.get_landmark_position(self.MOUTH_RIGHT)
        nose  = self.get_landmark_position(self.NOSE_TIP)
        l_eye = self.get_landmark_position(self.LEFT_EYE_OUTER)
        r_eye = self.get_landmark_position(self.RIGHT_EYE_OUTER)

        if not all([left, right, nose, l_eye, r_eye]):
            return 0.0

        face_width = abs(l_eye[0] - r_eye[0]) + 1e-6
        mouth_width = abs(left[0] - right[0])
        # Normiert: ~0.45 neutral, >0.55 Lächeln
        return mouth_width / face_width
    
    def get_eyebrow_raise_metric(self):
        """
        Augenbrauen-Hochziehen: Abstand Braue→Auge normiert auf Gesichtshöhe.
        """
        l_brow = self.get_landmark_position(self.LEFT_BROW_TOP)
        l_eye  = self.get_landmark_position(self.LEFT_EYE_TOP_L)
        r_brow = self.get_landmark_position(self.RIGHT_BROW_TOP)
        r_eye  = self.get_landmark_position(self.RIGHT_EYE_TOP_R)
        nose   = self.get_landmark_position(self.NOSE_TIP)
        upper  = self.get_landmark_position(10)  # Stirn oben

        if not all([l_brow, l_eye, r_brow, r_eye, nose, upper]):
            return 0.0

        face_height = abs(upper[1] - nose[1]) + 1e-6
        l_dist = abs(l_brow[1] - l_eye[1])
        r_dist = abs(r_brow[1] - r_eye[1])
        return ((l_dist + r_dist) / 2) / face_height

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
