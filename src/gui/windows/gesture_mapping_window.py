"""Gesten-Mapping Fenster"""
import tkinter as tk
from tkinter import ttk, messagebox

class GestureMappingWindow:
    """Fenster zum Konfigurieren von Gesten-zu-Aktion-Mappings"""
    def __init__(self, config, parent):
        self.config = config
        self.root = tk.Toplevel(parent)
        self.root.title("Gesten-Mapping")
        self.root.geometry("700x500")
        self.root.resizable(False, False)

        self.gesture_widgets = {}

        self.setup_ui()
        self.load_gestures()

    def setup_ui(self):
        """Erstellt UI"""
        # Header
        header = tk.Label(
            self.root,
            text="Ordne Gesten Aktionen zu",
            font=("Arial", 14, "bold")
        )
        header.pack(pady=10)

        # Info
        info = tk.Label(
            self.root,
            text="Aktiviere Gesten und wähle die zugehörige Aktion aus.",
            font=("Arial", 9),
            fg="#7f8c8d"
        )
        info.pack()

        # Scrollable Frame
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.gesture_frame = scrollable_frame

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(
            button_frame,
            text="Abbrechen",
            command=self.root.destroy,
            width=15
        ).pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(
            button_frame,
            text="Speichern",
            command=self.save_gestures,
            width=15,
            bg="#27ae60",
            fg="white"
        ).pack(side=tk.RIGHT)

    def load_gestures(self):
        """Lädt und zeigt alle Gesten"""
        gesture_actions = self.config.get_section('gesture_actions')
        available_actions = self.config.get('available_actions', [])

        gesture_names = {
            'mouth_open': 'Mund öffnen',
            'mouth_wide_open': 'Mund weit öffnen',
            'smile': 'Lächeln',
            'eyebrow_raise': 'Augenbrauen hochziehen',
            'head_tilt_left': 'Kopf nach links neigen',
            'head_tilt_right': 'Kopf nach rechts neigen'
        }

        action_names = {
            'left_click': 'Linksklick',
            'right_click': 'Rechtsklick',
            'double_click': 'Doppelklick',
            'middle_click': 'Mittelklick',
            'scroll_up': 'Hoch scrollen',
            'scroll_down': 'Runter scrollen',
            'drag_toggle': 'Drag umschalten',
            'key_enter': 'Enter drücken',
            'key_space': 'Leertaste drücken',
            'key_escape': 'Escape drücken',
            'key_left': 'Pfeil links',
            'key_right': 'Pfeil rechts',
            'key_up': 'Pfeil hoch',
            'key_down': 'Pfeil runter',
            'disabled': 'Deaktiviert'
        }

        row = 0
        for gesture_id, gesture_data in gesture_actions.items():
            # Frame für Geste
            gesture_frame = tk.LabelFrame(
                self.gesture_frame,
                text=gesture_names.get(gesture_id, gesture_id),
                padx=10,
                pady=10
            )
            gesture_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)

            # Enabled Checkbox
            enabled_var = tk.BooleanVar(value=gesture_data.get('enabled', False))
            enabled_check = tk.Checkbutton(
                gesture_frame,
                text="Aktiviert",
                variable=enabled_var
            )
            enabled_check.grid(row=0, column=0, sticky="w", pady=5)

            # Action Dropdown
            tk.Label(gesture_frame, text="Aktion:").grid(row=1, column=0, sticky="w")
            action_var = tk.StringVar(value=gesture_data.get('action', 'disabled'))
            action_dropdown = ttk.Combobox(
                gesture_frame,
                textvariable=action_var,
                values=[action_names.get(a, a) for a in available_actions],
                state="readonly",
                width=25
            )
            action_dropdown.grid(row=1, column=1, sticky="w", padx=5)

            # Map display names back to action IDs
            reverse_action_map = {v: k for k, v in action_names.items()}

            # Threshold Slider
            tk.Label(gesture_frame, text="Schwellwert:").grid(row=2, column=0, sticky="w", pady=5)
            threshold_var = tk.DoubleVar(value=gesture_data.get('threshold', 0.03))
            threshold_slider = tk.Scale(
                gesture_frame,
                from_=0.01,
                to=0.20,
                resolution=0.01,
                orient=tk.HORIZONTAL,
                variable=threshold_var,
                length=200
            )
            threshold_slider.grid(row=2, column=1, sticky="w", padx=5, pady=5)

            # Cooldown
            tk.Label(gesture_frame, text="Cooldown (Frames):").grid(row=3, column=0, sticky="w")
            cooldown_var = tk.IntVar(value=gesture_data.get('cooldown_frames', 15))
            cooldown_spinner = tk.Spinbox(
                gesture_frame,
                from_=1,
                to=60,
                textvariable=cooldown_var,
                width=10
            )
            cooldown_spinner.grid(row=3, column=1, sticky="w", padx=5)

            # Speichere Widgets
            self.gesture_widgets[gesture_id] = {
                'enabled': enabled_var,
                'action': action_var,
                'threshold': threshold_var,
                'cooldown': cooldown_var,
                'action_names': action_names,
                'reverse_action_map': reverse_action_map
            }

            row += 1

    def save_gestures(self):
        """Speichert Gesten-Konfiguration"""
        try:
            gesture_actions = {}

            for gesture_id, widgets in self.gesture_widgets.items():
                # Get display name and convert back to action ID
                action_display = widgets['action'].get()
                action_id = widgets['reverse_action_map'].get(action_display, action_display)

                gesture_actions[gesture_id] = {
                    'enabled': widgets['enabled'].get(),
                    'action': action_id,
                    'threshold': widgets['threshold'].get(),
                    'cooldown_frames': widgets['cooldown'].get()
                }

            self.config.update_section('gesture_actions', gesture_actions)
            self.config.save_config()

            messagebox.showinfo("Erfolg", "Gesten-Mapping wurde gespeichert!")
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")