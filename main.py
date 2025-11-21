import sys
from PyQt6.QtWidgets import QApplication
from src.core.tracker_engine import HeadTrackerWorker
from src.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Standard-Einstellung: Fenster schließen beendet App NICHT (wichtig für Tray)
    app.setQuitOnLastWindowClosed(False)

    # 1. Tracker Thread erstellen (aber noch nicht starten)
    tracker_thread = HeadTrackerWorker()

    # 2. GUI erstellen und Tracker übergeben
    window = MainWindow(tracker_thread)
    
    # 3. Tracker starten und GUI anzeigen
    tracker_thread.start()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()