"""System Tray Icon"""

class TrayIcon:
    """System Tray Integration (Platzhalter)"""
    def __init__(self, config):
        self.config = config
        self.enabled = config.get('features.tray_icon_enabled', False)
    
    def create(self):
        """Erstellt Tray Icon"""
        if not self.enabled:
            return
        # TODO: pystray implementierung
        pass
    
    def destroy(self):
        """Entfernt Tray Icon"""
        pass
