import cv2
import mediapipe as mp
import pyautogui
import numpy as np
from collections import deque

# Sicherheitseinstellung für PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001

class HeadTracker:
    def __init__(self):
        # MediaPipe Face Mesh initialisieren
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # Bildschirmgröße
        self.screen_w, self.screen_h = pyautogui.size()

        # Kalibrierung und Bewegungsparameter
        self.calibration_frames = 30
        self.calibrated = False
        self.reference_nose = None
        self.frame_count = 0

        # Bewegungsglättung
        self.smoothing_buffer_x = deque(maxlen=6)
        self.smoothing_buffer_y = deque(maxlen=6)

        # Empfindlichkeit und Bewegungsbereich
        self.sensitivity_x = 5
        self.sensitivity_y = 6
        self.movement_threshold = 0.003

        # Klick-Erkennung (Mund öffnen)
        self.mouth_open_threshold = 0.03
        self.click_cooldown = 0
        self.click_cooldown_frames = 15

        # Previous click state für Drag
        self.is_clicking = False

    def get_nose_position(self, landmarks, frame_w, frame_h):
        """Nose tip position (Landmark 1)"""
        nose = landmarks[1]
        return nose.x, nose.y

    def get_mouth_opening(self, landmarks):
        """Berechnet die Mundöffnung"""
        # Obere Lippe (13) und untere Lippe (14) der inneren Lippenkontur
        upper_lip = landmarks[13]
        lower_lip = landmarks[14]

        # Vertikaler Abstand
        mouth_opening = abs(upper_lip.y - lower_lip.y)
        return mouth_opening

    def smooth_movement(self, x, y):
        """Glättet die Mausbewegung"""
        self.smoothing_buffer_x.append(x)
        self.smoothing_buffer_y.append(y)

        smooth_x = np.mean(self.smoothing_buffer_x)
        smooth_y = np.mean(self.smoothing_buffer_y)

        return smooth_x, smooth_y

    def process_frame(self, frame):
        """Verarbeitet einen Frame und steuert die Maus"""
        frame_h, frame_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            landmarks = face_landmarks.landmark

            # Kalibrierung
            if not self.calibrated:
                self.frame_count += 1
                if self.frame_count == 1:
                    nose_x, nose_y = self.get_nose_position(landmarks, frame_w, frame_h)
                    self.reference_nose = (nose_x, nose_y)

                if self.frame_count >= self.calibration_frames:
                    self.calibrated = True
                    cv2.putText(frame, "Kalibriert! Bereit.", (20, 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, f"Kalibrierung... {self.frame_count}/{self.calibration_frames}", 
                              (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # Maussteuerung nach Kalibrierung
            if self.calibrated and self.reference_nose:
                # Aktuelle Nasenposition
                nose_x, nose_y = self.get_nose_position(landmarks, frame_w, frame_h)

                # Relative Bewegung zur Referenzposition
                delta_x = nose_x - self.reference_nose[0]
                delta_y = nose_y - self.reference_nose[1]

                # Bewegungsschwelle anwenden
                if abs(delta_x) > self.movement_threshold or abs(delta_y) > self.movement_threshold:
                    # Mausposition berechnen (invertierte Y-Achse)
                    smooth_x, smooth_y = self.smooth_movement(delta_x, delta_y)

                    mouse_x = self.screen_w / 2 + smooth_x * self.screen_w * self.sensitivity_x
                    mouse_y = self.screen_h / 2 + smooth_y * self.screen_h * self.sensitivity_y

                    # Bildschirmgrenzen
                    mouse_x = max(0, min(self.screen_w - 1, mouse_x))
                    mouse_y = max(0, min(self.screen_h - 1, mouse_y))

                    # Maus bewegen
                    pyautogui.moveTo(mouse_x, mouse_y)

                # Mundöffnung für Klicks
                mouth_opening = self.get_mouth_opening(landmarks)

                if self.click_cooldown > 0:
                    self.click_cooldown -= 1

                if mouth_opening > self.mouth_open_threshold and self.click_cooldown == 0:
                    if not self.is_clicking:
                        pyautogui.click()
                        self.is_clicking = True
                        self.click_cooldown = self.click_cooldown_frames
                        cv2.putText(frame, "CLICK!", (frame_w - 150, 60),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    self.is_clicking = False

                # Debug-Informationen
                cv2.putText(frame, f"Mouth: {mouth_opening:.3f}", (20, 100),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, f"Delta X: {delta_x:.3f} Y: {delta_y:.3f}", (20, 130),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Gesichts-Landmarks zeichnen
            self.mp_drawing.draw_landmarks(
                frame,
                face_landmarks,
                self.mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1)
            )

        # Steuerungshinweise
        cv2.putText(frame, "ESC: Beenden | R: Rekalibrieren", (20, frame_h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, "Mund oeffnen: Klick", (20, frame_h - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame

    def reset_calibration(self):
        """Setzt die Kalibrierung zurück"""
        self.calibrated = False
        self.frame_count = 0
        self.reference_nose = None
        self.smoothing_buffer_x.clear()
        self.smoothing_buffer_y.clear()

def main():
    # Webcam öffnen
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Fehler: Webcam konnte nicht geöffnet werden!")
        return

    tracker = HeadTracker()

    print("Head Tracking Maussteuerung")
    print("=" * 50)
    print("Anleitung:")
    print("- Schaue geradeaus für 1 Sekunde zur Kalibrierung")
    print("- Bewege deinen Kopf, um die Maus zu steuern")
    print("- Öffne den Mund für einen Klick")
    print("- Drücke 'R' für Rekalibrierung")
    print("- Drücke 'ESC' zum Beenden")
    print("=" * 50)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Fehler beim Lesen des Frames!")
            break

        # Frame spiegeln für intuitive Steuerung
        frame = cv2.flip(frame, 1)

        # Frame verarbeiten
        frame = tracker.process_frame(frame)

        # Anzeigen
        cv2.imshow('Head Tracking Mouse Control', frame)

        # Tastatureingaben
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        elif key == ord('r') or key == ord('R'):
            tracker.reset_calibration()
            print("Kalibrierung zurückgesetzt!")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()