from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, 
                             QWidget, QPushButton, QSystemTrayIcon, QMenu, QStyle)
from PyQt6.QtGui import QImage, QPixmap, QAction, QIcon
from PyQt6.QtCore import Qt
import cv2

class MainWindow(QMainWindow):
    def __init__(self, tracker_thread):
        super().__init__()
        self.tracker = tracker_thread

        # Fenster-Setup
        self.setWindowTitle("EyeAssist - Einstellungen")
        self.resize(800, 600)

        # Layout erstellen
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Label für Status
        self.status_label = QLabel("Status: Initialisiere...")
        layout.addWidget(self.status_label)

        # Label für Kamerabild (zum Testen)
        self.camera_label = QLabel("Kamera Feed")
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.camera_label)

        # Buttons
        btn_stop = QPushButton("Tracking Beenden")
        btn_stop.clicked.connect(self.close_app)
        layout.addWidget(btn_stop)

        # --- SYSTEM TRAY SETUP ---
        self.tray_icon = QSystemTrayIcon(self)
        # Hier solltest du später ein echtes Icon laden: QIcon("assets/icon.png")
        # Für jetzt nehmen wir ein Standard-Icon vom System
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        # Tray Menü (Rechtsklick auf Icon)
        tray_menu = QMenu()
        show_action = QAction("Einstellungen öffnen", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self.close_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # --- SIGNALE VERBINDEN ---
        # Wenn der Tracker ein Bild sendet -> update_image aufrufen
        self.tracker.image_signal.connect(self.update_image)
        self.tracker.status_signal.connect(self.update_status)

    def update_image(self, cv_img):
        """Wandelt OpenCV Bild in PyQt Bild um und zeigt es an."""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(qt_image).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))

    def update_status(self, text):
        self.status_label.setText(f"Status: {text}")

    # Überschreiben des Schließen-Events (X oben rechts)
    def closeEvent(self, event):
        # Wir wollen nicht beenden, sondern nur ins Tray minimieren!
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "EyeAssist läuft weiter",
            "Die Anwendung läuft im Hintergrund.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def close_app(self):
        """Wirkliches Beenden der App"""
        self.tracker.stop()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()