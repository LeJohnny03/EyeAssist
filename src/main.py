"""Haupteinstieg - Startet GUI-Anwendung"""
from utils.config_manager import ConfigManager
from gui.windows.main_window import MainWindow

def main():
    """Hauptfunktion - Startet GUI"""
    # Config laden/erstellen
    config = ConfigManager('config.json')
    
    # Starte GUI-Anwendung
    app = MainWindow(config)
    app.run()

if __name__ == "__main__":
    main()
