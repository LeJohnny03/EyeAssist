"""Haupt-Applikationslogik – Hybrid Head+Eye Tracking Backend"""
from core.tracker_engine import TrackerEngine
from core.gesture_recognizer import GestureRecognizer
from core.mouse_controller import MouseController
from gui.calibration_wizard import CalibrationWizard
from gui.overlay import Overlay
from utils.camera_helper import CameraHelper
import cv2

class HybridTrackingApp:
    """Haupt-Tracking-Anwendung mit Hybrid Head+Eye Tracking"""
    def __init__(self, config):
        self.config = config

        self.tracker            = TrackerEngine(config)
        self.gesture_recognizer = GestureRecognizer(config)
        self.mouse_controller   = MouseController(config)
        self.calibration_wizard = CalibrationWizard(config)
        self.overlay            = Overlay(config)
        self.camera             = CameraHelper(config)

        self.running      = False
        self.show_preview = config.get('gui.show_preview_window', True)

    def start(self):
        """Startet Tracking"""
        if not self.camera.open():
            raise Exception("Webcam konnte nicht geöffnet werden!")

        self.running = True

        if self.show_preview:
            cv2.namedWindow('Hybrid Tracking Preview')

        self.run_main_loop()
        return True

    def run_main_loop(self):
        """Haupt-Event-Loop"""
        while self.running:
            ret, frame = self.camera.read_frame()
            if not ret:
                break

            frame = self.process_frame(frame)

            if self.show_preview:
                cv2.imshow('Hybrid Tracking Preview', frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    def process_frame(self, frame):
        """Verarbeitet einzelnen Frame mit Hybrid Head+Eye Tracking"""
        face_detected, face_landmarks = self.tracker.process_frame(frame)

        if face_detected:
            if self.overlay.show_landmarks:
                self.tracker.draw_landmarks(frame, face_landmarks)

            # Head-Tracking (grobe Steuerung) – Nasenspitze als Referenz
            nose_tip  = self.tracker.get_nose_tip()
            upper_lip = self.tracker.get_upper_lip()
            lower_lip = self.tracker.get_lower_lip()

            # Iris-Delta (Feinjustierung) – relativ zum Augenmittelpunkt im aktuellen Frame
            iris_dx, iris_dy = self.tracker.get_iris_delta()

            # Kalibrierung – ausschließlich auf Kopfposition (Nase)
            if not self.calibration_wizard.is_complete:
                if self.calibration_wizard.update(nose_tip):
                    ref_pos = self.calibration_wizard.get_reference_position()
                    if ref_pos:
                        self.mouse_controller.set_reference_position(ref_pos[0], ref_pos[1])
                self.calibration_wizard.draw_progress(frame)

            # Hybrid-Maussteuerung nach Kalibrierung
            if self.calibration_wizard.is_complete and nose_tip:
                self.mouse_controller.move_mouse_hybrid(
                    nose_tip[0], nose_tip[1],
                    iris_dx, iris_dy
                )

                # Gesten-Erkennung (weiterhin kopfbasiert)
                landmarks_data = {
                    'nose_tip':       nose_tip,
                    'upper_lip':      upper_lip,
                    'lower_lip':      lower_lip,
                    'reference_nose': self.calibration_wizard.get_reference_position()
                }

                actions = self.gesture_recognizer.process_gestures(landmarks_data)

                if actions:
                    self.overlay.draw_click_indicator(frame)

                # Debug-Overlay
                delta_x, delta_y = self.mouse_controller.get_delta(nose_tip[0], nose_tip[1])
                mouth_opening = abs(upper_lip[1] - lower_lip[1]) if upper_lip and lower_lip else 0
                self.overlay.draw_tracking_info(
                    frame, delta_x, delta_y, mouth_opening,
                    self.mouse_controller.calibrated,
                    iris_dx, iris_dy
                )

        self.overlay.draw_controls(frame)
        return frame

    def recalibrate(self):
        """Rekalibriert Tracking"""
        self.calibration_wizard.reset()
        self.mouse_controller.reset_calibration()
        self.gesture_recognizer.reset()

    def stop(self):
        """Stoppt Tracking"""
        self.running = False
        self.camera.release()
        if self.show_preview:
            cv2.destroyAllWindows()
        self.tracker.close()
