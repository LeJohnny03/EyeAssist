"""Einstellungen-Fenster"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class SettingsWindow:
    """Fenster für alle Einstellungen"""
    def __init__(self, config, parent):
        self.config = config
        self.root = tk.Toplevel(parent)
        self.root.title("Einstellungen")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # Temporäre Werte für Änderungen
        self.temp_values = {}

        self.setup_ui()
        self.load_current_values()

    def setup_ui(self):
        """Erstellt UI"""
        # Notebook (Tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tabs
        self.create_mouse_tab(notebook)
        self.create_camera_tab(notebook)
        self.create_calibration_tab(notebook)
        self.create_general_tab(notebook)

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(
            button_frame,
            text="Zurücksetzen",
            command=self.reset_to_defaults,
            width=15
        ).pack(side=tk.LEFT)

        tk.Button(
            button_frame,
            text="Abbrechen",
            command=self.root.destroy,
            width=15
        ).pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(
            button_frame,
            text="Speichern",
            command=self.save_settings,
            width=15,
            bg="#27ae60",
            fg="white"
        ).pack(side=tk.RIGHT)

    def create_mouse_tab(self, notebook):
        """Tab für Maussteuerung"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Maussteuerung")

        # Sensitivität X
        self._create_slider(
            frame, "Horizontale Empfindlichkeit:", 
            "mouse.sensitivity_x", 0.1, 10.0, 0.1, 0
        )

        # Sensitivität Y
        self._create_slider(
            frame, "Vertikale Empfindlichkeit:", 
            "mouse.sensitivity_y", 0.1, 10.0, 0.1, 1
        )

        # Movement Threshold
        self._create_slider(
            frame, "Bewegungs-Schwelle:", 
            "mouse.movement_threshold", 0.001, 0.01, 0.001, 2
        )

        # Smoothing
        self._create_slider(
            frame, "Glättung (Buffer):", 
            "mouse.smoothing_buffer_size", 1, 15, 1, 3, use_int=True
        )

        # Checkboxen
        check_frame = tk.Frame(frame)
        check_frame.grid(row=4, column=0, columnspan=2, pady=20, sticky="w", padx=20)

        self.temp_values['mouse.invert_x'] = tk.BooleanVar()
        tk.Checkbutton(
            check_frame,
            text="X-Achse invertieren",
            variable=self.temp_values['mouse.invert_x']
        ).pack(anchor="w")

        self.temp_values['mouse.invert_y'] = tk.BooleanVar()
        tk.Checkbutton(
            check_frame,
            text="Y-Achse invertieren",
            variable=self.temp_values['mouse.invert_y']
        ).pack(anchor="w")

    def create_camera_tab(self, notebook):
        """Tab für Kamera-Einstellungen"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Kamera")

        # Kamera ID
        tk.Label(frame, text="Kamera ID:").grid(row=0, column=0, sticky="w", padx=20, pady=10)
        self.temp_values['camera.camera_id'] = tk.StringVar()
        tk.Spinbox(
            frame,
            from_=0,
            to=5,
            textvariable=self.temp_values['camera.camera_id'],
            width=10
        ).grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # Auflösung
        tk.Label(frame, text="Breite:").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        self.temp_values['camera.width'] = tk.StringVar()
        tk.Entry(
            frame,
            textvariable=self.temp_values['camera.width'],
            width=15
        ).grid(row=1, column=1, sticky="w", padx=20, pady=10)

        tk.Label(frame, text="Höhe:").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.temp_values['camera.height'] = tk.StringVar()
        tk.Entry(
            frame,
            textvariable=self.temp_values['camera.height'],
            width=15
        ).grid(row=2, column=1, sticky="w", padx=20, pady=10)

        # Horizontal spiegeln
        self.temp_values['camera.flip_horizontal'] = tk.BooleanVar()
        tk.Checkbutton(
            frame,
            text="Horizontal spiegeln",
            variable=self.temp_values['camera.flip_horizontal']
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=10)

    def create_calibration_tab(self, notebook):
        """Tab für Kalibrierung"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Kalibrierung")

        # Frames für Kalibrierung
        self._create_slider(
            frame, "Kalibrierungs-Frames:", 
            "calibration.frames_required", 10, 100, 5, 0, use_int=True
        )

        # Checkboxen
        check_frame = tk.Frame(frame)
        check_frame.grid(row=1, column=0, columnspan=2, pady=20, sticky="w", padx=20)

        self.temp_values['calibration.show_progress_bar'] = tk.BooleanVar()
        tk.Checkbutton(
            check_frame,
            text="Fortschrittsbalken anzeigen",
            variable=self.temp_values['calibration.show_progress_bar']
        ).pack(anchor="w")

        self.temp_values['calibration.auto_recalibrate_on_face_lost'] = tk.BooleanVar()
        tk.Checkbutton(
            check_frame,
            text="Auto-Rekalibrierung bei Gesichtsverlust",
            variable=self.temp_values['calibration.auto_recalibrate_on_face_lost']
        ).pack(anchor="w")

    def create_general_tab(self, notebook):
        """Tab für allgemeine Einstellungen"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Allgemein")

        # Checkboxen
        options = [
            ('general.start_minimized', 'Minimiert starten'),
            ('general.minimize_to_tray', 'In System Tray minimieren'),
            ('general.show_notifications', 'Benachrichtigungen anzeigen'),
            ('general.autostart_tracking', 'Tracking automatisch starten'),
            ('gui.show_preview_window', 'Vorschau-Fenster anzeigen'),
            ('gui.show_debug_info', 'Debug-Informationen anzeigen'),
            ('gui.show_landmarks', 'Face Landmarks anzeigen'),
            ('gui.show_fps', 'FPS anzeigen')
        ]

        for i, (key, label) in enumerate(options):
            self.temp_values[key] = tk.BooleanVar()
            tk.Checkbutton(
                frame,
                text=label,
                variable=self.temp_values[key]
            ).grid(row=i, column=0, sticky="w", padx=20, pady=5)

        # Export/Import Buttons
        button_frame = tk.Frame(frame)
        button_frame.grid(row=len(options), column=0, pady=20, padx=20, sticky="w")

        tk.Button(
            button_frame,
            text="Config exportieren",
            command=self.export_config,
            width=20
        ).pack(pady=5)

        tk.Button(
            button_frame,
            text="Config importieren",
            command=self.import_config,
            width=20
        ).pack(pady=5)

    def _create_slider(self, parent, label, config_key, min_val, max_val, 
                       resolution, row, use_int=False):
        """Hilfsfunktion zum Erstellen eines Sliders"""
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=20, pady=10)

        slider_frame = tk.Frame(parent)
        slider_frame.grid(row=row, column=1, sticky="ew", padx=20, pady=10)

        self.temp_values[config_key] = tk.DoubleVar() if not use_int else tk.IntVar()

        slider = tk.Scale(
            slider_frame,
            from_=min_val,
            to=max_val,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            variable=self.temp_values[config_key],
            length=250
        )
        slider.pack(side=tk.LEFT)

        value_label = tk.Label(slider_frame, textvariable=self.temp_values[config_key], width=8)
        value_label.pack(side=tk.LEFT, padx=5)

    def load_current_values(self):
        """Lädt aktuelle Werte aus Config"""
        for key, var in self.temp_values.items():
            value = self.config.get(key)
            if value is not None:
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(value))
                elif isinstance(var, tk.IntVar):
                    var.set(int(value))
                elif isinstance(var, tk.DoubleVar):
                    var.set(float(value))
                elif isinstance(var, tk.StringVar):
                    var.set(str(value))

    def save_settings(self):
        """Speichert Einstellungen"""
        try:
            for key, var in self.temp_values.items():
                if isinstance(var, tk.BooleanVar):
                    self.config.set(key, var.get())
                elif isinstance(var, (tk.IntVar, tk.DoubleVar)):
                    self.config.set(key, var.get())
                elif isinstance(var, tk.StringVar):
                    # Versuche zu int zu konvertieren wenn möglich
                    value = var.get()
                    try:
                        value = int(value)
                    except:
                        pass
                    self.config.set(key, value)

            self.config.save_config()
            messagebox.showinfo("Erfolg", "Einstellungen wurden gespeichert!")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")

    def reset_to_defaults(self):
        """Setzt auf Standardwerte zurück"""
        result = messagebox.askyesno(
            "Zurücksetzen",
            "Wirklich alle Einstellungen zurücksetzen?"
        )
        if result:
            self.config.reset_to_defaults()
            self.load_current_values()
            messagebox.showinfo("Erfolg", "Einstellungen wurden zurückgesetzt!")

    def export_config(self):
        """Exportiert Config"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            if self.config.export_config(filepath):
                messagebox.showinfo("Erfolg", "Config wurde exportiert!")
            else:
                messagebox.showerror("Fehler", "Export fehlgeschlagen!")

    def import_config(self):
        """Importiert Config"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            if self.config.import_config(filepath):
                self.load_current_values()
                messagebox.showinfo("Erfolg", "Config wurde importiert!")
            else:
                messagebox.showerror("Fehler", "Import fehlgeschlagen!")