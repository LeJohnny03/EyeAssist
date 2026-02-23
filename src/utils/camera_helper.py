"""Webcam-Verwaltung und Frame-Verarbeitung"""
import cv2

class CameraHelper:
    """Verwaltet Webcam-Zugriff und Frame-Bereitstellung"""
    def __init__(self, config):
        self.config = config
        self.camera_id = config.get('camera.camera_id', 0)
        self.width = config.get('camera.width', 640)
        self.height = config.get('camera.height', 480)
        self.flip_horizontal = config.get('camera.flip_horizontal', True)
        self.cap = None
        self.is_opened = False

    def open(self):
        """Öffnet Webcam"""
        self.cap = cv2.VideoCapture(self.camera_id)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.is_opened = True
            return True
        return False

    def read_frame(self):
        """Liest Frame von Webcam"""
        if not self.is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if ret and self.flip_horizontal:
            frame = cv2.flip(frame, 1)
        return ret, frame

    def release(self):
        """Gibt Webcam frei"""
        if self.cap is not None:
            self.cap.release()
            self.is_opened = False

    def get_frame_dimensions(self):
        """Gibt Frame-Dimensionen zurück"""
        if self.cap is not None and self.is_opened:
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return width, height
        return self.width, self.height

    def __del__(self):
        """Destructor: Gibt Ressourcen frei"""
        self.release()