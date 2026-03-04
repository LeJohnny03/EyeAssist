"""Kalibrierungs-Wizard"""
import cv2


class CalibrationWizard:
    def __init__(self, config):
        self.config = config
        self.calibration_frames = config.get('calibration.frames_required', 30)
        self.show_progress_bar = config.get('calibration.show_progress_bar', True)
        self.current_frame = 0
        self.is_complete = False
        self.reference_position = None
        self._sum = [0.0, 0.0]
        self._count = 0

    def update(self, position):
        """Aktualisiert Kalibrierung – position ist (yaw, pitch) in Grad"""
        if self.is_complete:
            return True

        self.current_frame += 1

        # Durchschnitt über alle Kalibrierungsframes bilden
        if position is not None:
            self._sum[0] += position[0]
            self._sum[1] += position[1]
            self._count += 1

        if self.current_frame >= self.calibration_frames:
            if self._count > 0:
                self.reference_position = (
                    self._sum[0] / self._count,
                    self._sum[1] / self._count
                )
            self.is_complete = True
            return True

        return False

    def get_progress(self):
        return min(1.0, self.current_frame / self.calibration_frames)

    def get_reference_position(self):
        return self.reference_position

    def reset(self):
        self.current_frame = 0
        self.is_complete = False
        self.reference_position = None
        self._sum = [0.0, 0.0]
        self._count = 0

    def draw_progress(self, frame):
        h, w = frame.shape[:2]
        calibrating_color = tuple(self.config.get('colors.calibrating', [0, 255, 255]))
        calibrated_color  = tuple(self.config.get('colors.calibrated',  [0, 255, 0]))

        if not self.is_complete:
            text  = f"Kalibrierung... {self.current_frame}/{self.calibration_frames}"
            color = calibrating_color
        else:
            text  = "Kalibriert! Bereit."
            color = calibrated_color

        cv2.putText(frame, text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if self.show_progress_bar and not self.is_complete:
            bar_width, bar_height = w - 40, 20
            bar_x, bar_y = 20, 80
            bar_bg = tuple(self.config.get('colors.progress_bar_bg', [50, 50, 50]))
            cv2.rectangle(frame, (bar_x, bar_y),
                          (bar_x + bar_width, bar_y + bar_height), bar_bg, -1)
            progress_width = int(bar_width * self.get_progress())
            cv2.rectangle(frame, (bar_x, bar_y),
                          (bar_x + progress_width, bar_y + bar_height), color, -1)
