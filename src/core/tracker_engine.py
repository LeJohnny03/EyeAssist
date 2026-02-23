import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass


@dataclass
class TrackResult:
    has_face: bool
    frame_w: int
    frame_h: int

    # Nase in Pixel-Koordinaten (für Mouse Mapping + Debug)
    nose_px: tuple[int, int] | None = None

    # Augen-Landmarks (normiert 0..1) für Blink
    left_eye_top: tuple[float, float] | None = None
    left_eye_bottom: tuple[float, float] | None = None
    right_eye_top: tuple[float, float] | None = None
    right_eye_bottom: tuple[float, float] | None = None
    
    landmarks: list | None = None

    # Debug
    eye_dist: float | None = None


class TrackerEngine:
    """
    Verantwortlich für:
    - Webcam-Frame lesen
    - FaceMesh-Landmarks bestimmen
    - relevante Punkte extrahieren (Nase + Auge)
    - Debug Rendering + Window Handling
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg

        mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=cfg["tracking"]["min_detection_confidence"],
            min_tracking_confidence=cfg["tracking"]["min_tracking_confidence"],
        )

    def read_frame(self, cap):
        ok, frame = cap.read()
        if not ok:
            return None

        # Spiegeln damit links auch links ist
        if self.cfg["camera"]["flip"]:
            frame = cv2.flip(frame, 1)

        self._last_frame = frame
        return frame

    def process(self, frame) -> TrackResult:
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        track = TrackResult(has_face=False, frame_w=w, frame_h=h)

        if not results.multi_face_landmarks:
            return track

        lm = results.multi_face_landmarks[0].landmark
        track.landmarks = lm 
        track.has_face = True

        # Nose (dein Skript: 4)
        nose = lm[4]
        track.nose_px = (int(nose.x * w), int(nose.y * h))

        # Left eye top/bottom
        lt = lm[159]
        lb = lm[145]
        track.left_eye_top = (lt.x, lt.y)
        track.left_eye_bottom = (lb.x, lb.y)

        # Right eye top/bottom (MediaPipe FaceMesh)
        # Häufig stabile Punkte: 386 (oben), 374 (unten)
        rt = lm[386]
        rb = lm[374]
        track.right_eye_top = (rt.x, rt.y)
        track.right_eye_bottom = (rb.x, rb.y)

        return track

    def draw_debug(self, frame, track: TrackResult, gestures) -> np.ndarray:
        if not self.cfg["ui"]["debug_overlay"]:
            return frame

        out = frame

        # Nase + Zentrum
        if track.has_face and track.nose_px:
            nx, ny = track.nose_px
            cv2.circle(out, (nx, ny), 5, (0, 255, 255), -1)
            cv2.circle(out, (track.frame_w // 2, track.frame_h // 2), 3, (200, 200, 200), -1)

        # Eye dist text (von GestureRecognizer berechnet)
        if gestures.last_eye_dist is not None:
            cv2.putText(
                out,
                f"Eye: {gestures.last_eye_dist:.3f}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

        # Click Feedback
        if gestures.last_event == "LEFT_CLICK":
            cv2.putText(
                out,
                "CLICK!",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0, 0, 255),
                3,
            )

        return out

    def show(self, frame):
        cv2.imshow(self.window_name, frame)

    def should_quit(self) -> bool:
        return (cv2.waitKey(1) & 0xFF) == 27

    def release(self, cap):
        try:
            cap.release()
        except Exception:
            pass
        cv2.destroyAllWindows()
        try:
            self.face_mesh.close()
        except Exception:
            pass
        
        
    def close(self):
        try:
            self.face_mesh.close()
        except Exception:
            pass
