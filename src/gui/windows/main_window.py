"""Hauptfenster der GUI-Anwendung"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from gui.windows.settings_window import SettingsWindow
from gui.windows.gesture_mapping_window import GestureMappingWindow
from gui.windows.preview_window import PreviewWindow
from core.application import EyeTrackingApp

class MainWindow:
    """Hauptfenster der Anwendung"""
    def __init__(self, config):
        self.config = config
        self.root = tk.Tk()
        self.root.title("Head Tracking Mouse Control")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Tracking-Anwendung
        self.tracking_app = None
        self.tracking_thread = None
        self.is_tracking = False

        # Fenster
        self.settings_window = None
        self.gesture_window = None
        self.preview_window = None

        self.setup_ui()
        self.apply_theme()

        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Erstellt UI-Elemente"""
        # Header
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame, 
            text="Head Tracking Mouse Control",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=20)

        # Main Content
        content_frame = tk.Frame(self.root, padx=20, pady=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Status
        status_frame = tk.LabelFrame(content_frame, text="Status", padx=10, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = tk.Label(
            status_frame,
            text="● Bereit",
            font=("Arial", 12),
            fg="#27ae60"
        )
        self.status_label.pack()

        # Control Buttons
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill=tk.X, pady=(0, 15))

        self.start_button = tk.Button(
            button_frame,
            text="▶ Tracking Starten",
            command=self.toggle_tracking,
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            height=2,
            cursor="hand2"
        )
        self.start_button.pack(fill=tk.X)

        # Settings Buttons
        settings_frame = tk.Frame(content_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Button(
            settings_frame,
            text="⚙ Einstellungen",
            command=self.open_settings,
            font=("Arial", 11),
            width=20,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(
            settings_frame,
            text="🎯 Gesten-Mapping",
            command=self.open_gesture_mapping,
            font=("Arial", 11),
            width=20,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        # Additional Options
        options_frame = tk.Frame(content_frame)
        options_frame.pack(fill=tk.X)

        tk.Button(
            options_frame,
            text="📹 Vorschau",
            command=self.toggle_preview,
            font=("Arial", 10),
            width=15,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(
            options_frame,
            text="🔄 Rekalibrieren",
            command=self.recalibrate,
            font=("Arial", 10),
            width=15,
            cursor="hand2",
            state=tk.DISABLED
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.recalibrate_button = options_frame.winfo_children()[-1]

        # Footer
        footer_frame = tk.Frame(self.root, bg="#ecf0f1", height=40)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        footer_frame.pack_propagate(False)

        footer_label = tk.Label(
            footer_frame,
            text="v1.0 | Powered by MediaPipe",
            font=("Arial", 8),
            bg="#ecf0f1",
            fg="#7f8c8d"
        )
        footer_label.pack(pady=10)

    def toggle_tracking(self):
        """Startet/Stoppt Tracking"""
        if not self.is_tracking:
            self.start_tracking()
        else:
            self.stop_tracking()

    def start_tracking(self):
        """Startet Head-Tracking"""
        try:
            # Erstelle Tracking-App
            self.tracking_app = EyeTrackingApp(self.config)

            # Starte in separatem Thread
            self.tracking_thread = threading.Thread(target=self._run_tracking, daemon=True)
            self.tracking_thread.start()

            # Update UI
            self.is_tracking = True
            self.start_button.config(
                text="■ Tracking Stoppen",
                bg="#e74c3c"
            )
            self.status_label.config(text="● Aktiv", fg="#27ae60")
            self.recalibrate_button.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Fehler", f"Tracking konnte nicht gestartet werden:\n{e}")

    def _run_tracking(self):
        """Führt Tracking aus (läuft in Thread)"""
        try:
            self.tracking_app.start()
        except Exception as e:
            print(f"Tracking-Fehler: {e}")
            self.root.after(0, self.stop_tracking)

    def stop_tracking(self):
        """Stoppt Head-Tracking"""
        if self.tracking_app:
            self.tracking_app.stop()
            self.tracking_app = None

        self.is_tracking = False
        self.start_button.config(
            text="▶ Tracking Starten",
            bg="#27ae60"
        )
        self.status_label.config(text="● Bereit", fg="#95a5a6")
        self.recalibrate_button.config(state=tk.DISABLED)

    def recalibrate(self):
        """Rekalibriert Tracking"""
        if self.tracking_app:
            self.tracking_app.recalibrate()
            messagebox.showinfo("Rekalibrierung", "Kalibrierung wurde zurückgesetzt!")

    def open_settings(self):
        """Öffnet Einstellungen-Fenster"""
        if self.settings_window is None or not self.settings_window.root.winfo_exists():
            self.settings_window = SettingsWindow(self.config, self.root)

    def open_gesture_mapping(self):
        """Öffnet Gesten-Mapping-Fenster"""
        if self.gesture_window is None or not self.gesture_window.root.winfo_exists():
            self.gesture_window = GestureMappingWindow(self.config, self.root)

    def toggle_preview(self):
        """Öffnet/Schließt Vorschau-Fenster"""
        if self.preview_window is None:
            show_preview = self.config.get('gui.show_preview_window', True)
            self.config.set('gui.show_preview_window', not show_preview)
            self.config.save_config()
            messagebox.showinfo("Vorschau", "Vorschau-Einstellung wurde geändert. Starte Tracking neu.")

    def apply_theme(self):
        """Wendet Theme an"""
        theme = self.config.get('gui.theme', 'light')
        # TODO: Implement dark theme

    def on_closing(self):
        """Wird beim Schließen aufgerufen"""
        if self.is_tracking:
            result = messagebox.askyesno(
                "Tracking aktiv",
                "Tracking ist noch aktiv. Wirklich beenden?"
            )
            if not result:
                return
            self.stop_tracking()

        self.root.destroy()

    def run(self):
        """Startet GUI-Loop"""
        self.root.mainloop()