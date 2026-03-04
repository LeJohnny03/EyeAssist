"""Haupt-Applikationslogik - Tracking Backend"""
from core.tracker_engine import TrackerEngine
from core.gesture_recognizer import GestureRecognizer
from core.mouse_controller import MouseController
from gui.calibration_wizard import CalibrationWizard
from gui.overlay import Overlay
from utils.camera_helper import CameraHelper
import cv2


class HeadTrackingApp:
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
        if not self.camera.open():
            raise Exception("Webcam konnte nicht geöffnet werden!")
        self.running = True
        if self.show_preview:
            cv2.namedWindow('Head Tracking Preview')
        self.run_main_loop()
        return True

    def run_main_loop(self):
        while self.running:
            ret, frame = self.camera.read_frame()
            if not ret:
                break
            frame = self.process_frame(frame)
            if self.show_preview:
                cv2.imshow('Head Tracking Preview', frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    def process_frame(self, frame):
        face_detected, face_landmarks = self.tracker.process_frame(frame)

        if face_detected:
            if self.overlay.show_landmarks:
                self.tracker.draw_landmarks(frame, face_landmarks)

            head_pose = self.tracker.get_head_pose()  # (pitch, yaw, roll) in Grad
            upper_lip = self.tracker.get_upper_lip()
            lower_lip = self.tracker.get_lower_lip()
            nose_tip  = self.tracker.get_nose_tip()   # nur für Gesten benötigt

            # Steuerungsgröße: (yaw, pitch)
            pose_2d = (head_pose[1], head_pose[0]) if head_pose else None

            # Kalibrierung
            if not self.calibration_wizard.is_complete:
                if self.calibration_wizard.update(pose_2d):
                    ref_pos = self.calibration_wizard.get_reference_position()
                    if ref_pos:
                        self.mouse_controller.set_reference_position(ref_pos[0], ref_pos[1])
                self.calibration_wizard.draw_progress(frame)

            # Maussteuerung
            if self.calibration_wizard.is_complete and pose_2d:
                self.mouse_controller.move_mouse(pose_2d[0], pose_2d[1])

                landmarks_data = {
                    'nose_tip':       nose_tip,
                    'upper_lip':      upper_lip,
                    'lower_lip':      lower_lip,
                    'reference_nose': self.calibration_wizard.get_reference_position()
                }
                actions = self.gesture_recognizer.process_gestures(landmarks_data)
                if actions:
                    self.overlay.draw_click_indicator(frame)

                delta_x, delta_y = self.mouse_controller.get_delta(pose_2d[0], pose_2d[1])
                mouth_opening = abs(upper_lip[1] - lower_lip[1]) if upper_lip and lower_lip else 0
                self.overlay.draw_tracking_info(
                    frame, delta_x, delta_y, mouth_opening,
                    self.mouse_controller.calibrated
                )

        self.overlay.draw_controls(frame)
        return frame

    def recalibrate(self):
        self.calibration_wizard.reset()
        self.mouse_controller.reset_calibration()
        self.gesture_recognizer.reset()

    def stop(self):
        self.running = False
        self.camera.release()
        if self.show_preview:
            cv2.destroyAllWindows()
        self.tracker.close()
