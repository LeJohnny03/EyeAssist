# Klasse für MediaPipe, Kamera-Zugriff, Head-Pose-Berechnung
import cv2
import time
from PyQt6.QtCore import QThread, pyqtSignal

class HeadTrackerWorker(QThread):
    # Signale definieren: Damit kommunizieren wir mit der GUI
    # Wir senden z.B. das Kamerabild (fürs Overlay) und Status-Infos
    image_signal = pyqtSignal(object) 
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        """Diese Methode läuft parallel zur GUI in einem eigenen Thread."""
        cap = cv2.VideoCapture(0)
        
        self.status_signal.emit("Kamera gestartet...")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                self.status_signal.emit("Fehler: Keine Kamera!")
                time.sleep(1)
                continue

            # --- HIER KOMMT SPÄTER DEIN MEDIAPIPE CODE REIN ---
            # Aktuell machen wir nur einen Dummy-Test:
            # Wir spiegeln das Bild und senden es an die GUI
            frame = cv2.flip(frame, 1)
            
            # ... Head Tracking Berechnungen ...
            # ... Maus bewegen ...

            # Bild an GUI senden (optional, falls man sich sehen will)
            self.image_signal.emit(frame)
            
            # Wichtig: Nicht 100% CPU verbrauchen
            time.sleep(0.01) 

        # Aufräumen wenn Thread stoppt
        cap.release()
        self.status_signal.emit("Tracker gestoppt.")

    def stop(self):
        """Methode um den Thread sauber zu beenden"""
        self.running = False
        self.wait()