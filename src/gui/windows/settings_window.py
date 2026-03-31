"""Einstellungen-Fenster – modernes Design mit Hell/Dunkel-Modus"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ─── Farbpaletten ────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "bg":           "#f7f6f2",
        "surface":      "#ffffff",
        "surface2":     "#f3f0ec",
        "border":       "#d4d1ca",
        "text":         "#28251d",
        "text_muted":   "#7a7974",
        "accent":       "#01696f",
        "accent_hover": "#0c4e54",
        "accent_fg":    "#ffffff",
        "danger":       "#a12c7b",
        "danger_fg":    "#ffffff",
        "neutral":      "#e6e4df",
        "neutral_fg":   "#28251d",
        "slider_trough":"#dcd9d5",
        "check_active": "#01696f",
        "tab_active":   "#ffffff",
        "tab_inactive": "#f3f0ec",
        "tab_text":     "#28251d",
    },
    "dark": {
        "bg":           "#171614",
        "surface":      "#1c1b19",
        "surface2":     "#22211f",
        "border":       "#393836",
        "text":         "#cdccca",
        "text_muted":   "#797876",
        "accent":       "#4f98a3",
        "accent_hover": "#227f8b",
        "accent_fg":    "#171614",
        "danger":       "#d163a7",
        "danger_fg":    "#171614",
        "neutral":      "#2d2c2a",
        "neutral_fg":   "#cdccca",
        "slider_trough":"#2d2c2a",
        "check_active": "#4f98a3",
        "tab_active":   "#1c1b19",
        "tab_inactive": "#141312",
        "tab_text":     "#cdccca",
    },
}


class SettingsWindow:
    """Einstellungen-Fenster mit modernem Design und Hell/Dunkel-Modus"""

    def __init__(self, config, parent):
        self.config = config
        self.theme_name = config.get("gui.theme") or "light"
        self.c = THEMES[self.theme_name]

        self.root = tk.Toplevel(parent)
        self.root.title("EyeAssist – Einstellungen")
        self.root.geometry("720x580")
        self.root.resizable(True, True)
        self.root.minsize(600, 480)

        self.temp_values = {}
        self._all_widgets = []  # für Theme-Refresh

        self._apply_root_theme()
        self.setup_ui()
        self.load_current_values()

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _apply_root_theme(self):
        self.root.configure(bg=self.c["bg"])
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook",
                        background=self.c["bg"],
                        borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab",
                        background=self.c["tab_inactive"],
                        foreground=self.c["tab_text"],
                        padding=[16, 8],
                        font=("Segoe UI", 10),
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", self.c["tab_active"]),
                               ("active",   self.c["surface2"])],
                  foreground=[("selected", self.c["accent"])])
        style.configure("TFrame", background=self.c["surface"])
        style.configure("Flat.TFrame", background=self.c["bg"])
        style.configure("TScrollbar",
                        background=self.c["surface2"],
                        troughcolor=self.c["bg"],
                        borderwidth=0,
                        arrowcolor=self.c["text_muted"])

    def _toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.c = THEMES[self.theme_name]
        # Config-Variable aktualisieren (wird beim Speichern persistent)
        if "gui.theme" in self.temp_values:
            self.temp_values["gui.theme"].set(self.theme_name)
        self._apply_root_theme()
        # Alle registrierten Widgets neu einfärben
        for fn in self._all_widgets:
            fn()

    def _reg(self, fn):
        """Registriert eine Refresh-Funktion für Theme-Wechsel."""
        self._all_widgets.append(fn)
        fn()

    # ─── UI-Aufbau ───────────────────────────────────────────────────────────

    def setup_ui(self):
        # ── Kopfzeile ──
        header = tk.Frame(self.root)
        header.pack(fill=tk.X, padx=0, pady=0)
        self._reg(lambda w=header: w.configure(bg=self.c["surface"]))

        title_lbl = tk.Label(header, text="⚙  Einstellungen, BETA: Manche Änderungen werde möglicherweise nicht angewendet.",
                             font=("Segoe UI Semibold", 14),
                             anchor="w", padx=20, pady=14)
        self._reg(lambda w=title_lbl: w.configure(
            bg=self.c["surface"], fg=self.c["text"]))
        title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Theme-Toggle
        self.theme_btn = tk.Button(header, text="🌙",
                                   font=("Segoe UI", 13),
                                   bd=0, relief=tk.FLAT, padx=12,
                                   command=self._toggle_theme, cursor="hand2")
        self._reg(lambda w=self.theme_btn: w.configure(
            bg=self.c["surface"], fg=self.c["text"],
            activebackground=self.c["surface2"],
            activeforeground=self.c["accent"]))
        self.theme_btn.pack(side=tk.RIGHT, padx=10)

        # Trennlinie unter Header
        sep = tk.Frame(self.root, height=1)
        self._reg(lambda w=sep: w.configure(bg=self.c["border"]))
        sep.pack(fill=tk.X)

        # ── Notebook ──
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        self.create_mouse_tab(self.notebook)
        self.create_camera_tab(self.notebook)
        self.create_tracking_tab(self.notebook)
        self.create_calibration_tab(self.notebook)
        self.create_gestures_tab(self.notebook)
        self.create_hotkeys_tab(self.notebook)
        self.create_general_tab(self.notebook)

        # ── Footer-Buttons ──
        sep2 = tk.Frame(self.root, height=1)
        self._reg(lambda w=sep2: w.configure(bg=self.c["border"]))
        sep2.pack(fill=tk.X, padx=0)

        btn_bar = tk.Frame(self.root)
        self._reg(lambda w=btn_bar: w.configure(bg=self.c["bg"]))
        btn_bar.pack(fill=tk.X, padx=16, pady=12)

        self._make_btn(btn_bar, "↺  Zurücksetzen",
                       self.reset_to_defaults, "neutral").pack(side=tk.LEFT)
        self._make_btn(btn_bar, "✕  Abbrechen",
                       self.root.destroy, "neutral").pack(side=tk.RIGHT, padx=(8, 0))
        self._make_btn(btn_bar, "✓  Speichern",
                       self.save_settings, "accent").pack(side=tk.RIGHT)

    # ─── Tab-Hilfsfunktionen ─────────────────────────────────────────────────

    def _scrollable_frame(self, notebook, tab_title):
        """Erstellt einen scrollbaren Tab-Frame."""
        outer = ttk.Frame(notebook)
        notebook.add(outer, text=tab_title)

        canvas = tk.Canvas(outer, bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", _resize)

        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        self._reg(lambda c=canvas, f=inner: (
            c.configure(bg=self.c["surface"]),
            f.configure(bg=self.c["surface"])
        ))
        return inner

    def _section(self, parent, title):
        """Erstellt eine beschriftete Abschnittsgruppe."""
        wrapper = tk.Frame(parent)
        self._reg(lambda w=wrapper: w.configure(bg=self.c["surface"]))
        wrapper.pack(fill=tk.X, padx=20, pady=(16, 4))

        lbl = tk.Label(wrapper, text=title.upper(),
                       font=("Segoe UI", 8, "bold"), anchor="w")
        self._reg(lambda w=lbl: w.configure(
            bg=self.c["surface"], fg=self.c["accent"]))
        lbl.pack(fill=tk.X, pady=(0, 6))

        sep = tk.Frame(wrapper, height=1)
        self._reg(lambda w=sep: w.configure(bg=self.c["border"]))
        sep.pack(fill=tk.X, pady=(0, 8))

        card = tk.Frame(wrapper, bd=0)
        self._reg(lambda w=card: w.configure(bg=self.c["surface2"]))
        card.pack(fill=tk.X)
        return card

    def _row(self, parent, row_idx):
        """Gibt einen hellen/dunklen Zeilen-Frame zurück."""
        bg_key = "surface" if row_idx % 2 == 0 else "surface2"
        f = tk.Frame(parent, pady=6)
        self._reg(lambda w=f, k=bg_key: w.configure(bg=self.c[k]))
        f.pack(fill=tk.X, padx=2)
        return f, bg_key

    def _label(self, parent, text, bg_key="surface2", muted=False):
        lbl = tk.Label(parent, text=text,
                       font=("Segoe UI", 10), anchor="w")
        self._reg(lambda w=lbl, k=bg_key: w.configure(
            bg=self.c[k],
            fg=self.c["text_muted"] if muted else self.c["text"]))
        lbl.pack(side=tk.LEFT, padx=(12, 6))
        return lbl

    def _make_btn(self, parent, text, cmd, style="neutral"):
        b = tk.Button(parent, text=text, command=cmd,
                      font=("Segoe UI", 10), bd=0, relief=tk.FLAT,
                      padx=16, pady=8, cursor="hand2")
        if style == "accent":
            self._reg(lambda w=b: w.configure(
                bg=self.c["accent"], fg=self.c["accent_fg"],
                activebackground=self.c["accent_hover"],
                activeforeground=self.c["accent_fg"]))
        elif style == "danger":
            self._reg(lambda w=b: w.configure(
                bg=self.c["danger"], fg=self.c["danger_fg"],
                activebackground=self.c["danger"],
                activeforeground=self.c["danger_fg"]))
        else:
            self._reg(lambda w=b: w.configure(
                bg=self.c["neutral"], fg=self.c["neutral_fg"],
                activebackground=self.c["border"],
                activeforeground=self.c["text"]))
        return b

    # ─── Slider & Checkbox ───────────────────────────────────────────────────

    def _create_slider(self, parent, label, config_key,
                       min_val, max_val, resolution, row_idx,
                       use_int=False, hint=""):
        row, bg_key = self._row(parent, row_idx)
        self._label(row, label, bg_key)

        var = tk.IntVar() if use_int else tk.DoubleVar()
        self.temp_values[config_key] = var

        val_lbl = tk.Label(row, font=("Segoe UI Semibold", 10), width=6, anchor="e")
        self._reg(lambda w=val_lbl, k=bg_key: w.configure(
            bg=self.c[k], fg=self.c["accent"]))
        val_lbl.pack(side=tk.RIGHT, padx=(0, 12))

        def _upd(*_):
            v = var.get()
            val_lbl.config(text=f"{v:.3f}" if not use_int else str(v))
        var.trace_add("write", _upd)

        slider = tk.Scale(row, from_=min_val, to=max_val,
                          resolution=resolution, orient=tk.HORIZONTAL,
                          variable=var, showvalue=False, length=220,
                          bd=0, highlightthickness=0)
        self._reg(lambda w=slider, k=bg_key: w.configure(
            bg=self.c[k], fg=self.c["accent"],
            troughcolor=self.c["slider_trough"],
            activebackground=self.c["accent_hover"]))
        slider.pack(side=tk.RIGHT, padx=4)

        if hint:
            h = tk.Label(row, text=hint, font=("Segoe UI", 8))
            self._reg(lambda w=h, k=bg_key: w.configure(
                bg=self.c[k], fg=self.c["text_muted"]))
            h.pack(side=tk.RIGHT, padx=(0, 4))

    def _create_checkbox(self, parent, label, config_key, row_idx, hint=""):
        row, bg_key = self._row(parent, row_idx)
        var = tk.BooleanVar()
        self.temp_values[config_key] = var

        cb = tk.Checkbutton(row, text=label,
                            variable=var, font=("Segoe UI", 10),
                            bd=0, relief=tk.FLAT, anchor="w",
                            cursor="hand2")
        self._reg(lambda w=cb, k=bg_key: w.configure(
            bg=self.c[k], fg=self.c["text"],
            selectcolor=self.c["check_active"],
            activebackground=self.c[k],
            activeforeground=self.c["accent"]))
        cb.pack(side=tk.LEFT, padx=(12, 0), fill=tk.X)

        if hint:
            h = tk.Label(row, text=hint, font=("Segoe UI", 8))
            self._reg(lambda w=h, k=bg_key: w.configure(
                bg=self.c[k], fg=self.c["text_muted"]))
            h.pack(side=tk.LEFT, padx=4)

    def _create_spinbox(self, parent, label, config_key, from_, to_, row_idx):
        row, bg_key = self._row(parent, row_idx)
        self._label(row, label, bg_key)
        var = tk.StringVar()
        self.temp_values[config_key] = var
        sb = tk.Spinbox(row, from_=from_, to=to_, textvariable=var,
                        width=8, font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        self._reg(lambda w=sb, k=bg_key: w.configure(
            bg=self.c["surface"], fg=self.c["text"],
            insertbackground=self.c["text"],
            buttonbackground=self.c["surface2"]))
        sb.pack(side=tk.LEFT, padx=8)

    def _create_entry(self, parent, label, config_key, row_idx, width=12):
        row, bg_key = self._row(parent, row_idx)
        self._label(row, label, bg_key)
        var = tk.StringVar()
        self.temp_values[config_key] = var
        e = tk.Entry(row, textvariable=var, width=width,
                     font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        self._reg(lambda w=e, k=bg_key: w.configure(
            bg=self.c["surface"], fg=self.c["text"],
            insertbackground=self.c["text"]))
        e.pack(side=tk.LEFT, padx=8)

    def _create_combobox(self, parent, label, config_key, choices, row_idx):
        row, bg_key = self._row(parent, row_idx)
        self._label(row, label, bg_key)
        var = tk.StringVar()
        self.temp_values[config_key] = var
        cb = ttk.Combobox(row, textvariable=var, values=choices,
                          state="readonly", width=18, font=("Segoe UI", 10))
        cb.pack(side=tk.LEFT, padx=8)

    # ─── Tabs ────────────────────────────────────────────────────────────────

    def create_mouse_tab(self, notebook):
        f = self._scrollable_frame(notebook, "🖱  Maus")

        sec = self._section(f, "Empfindlichkeit")
        self._create_slider(sec, "Horizontal (Kopf):",   "mouse.sensitivity_x",     0.1, 20.0, 0.1, 0, hint="Kopf-X")
        self._create_slider(sec, "Vertikal (Kopf):",     "mouse.sensitivity_y",     0.1, 20.0, 0.1, 1, hint="Kopf-Y")
        self._create_slider(sec, "Horizontal (Iris):",   "mouse.iris_sensitivity_x", 0.1, 10.0, 0.1, 2, hint="Iris-X")
        self._create_slider(sec, "Vertikal (Iris):",     "mouse.iris_sensitivity_y", 0.1, 10.0, 0.1, 3, hint="Iris-Y")

        sec2 = self._section(f, "Filter & Glättung")
        self._create_slider(sec2, "Bewegungs-Schwelle:",  "mouse.movement_threshold", 0.001, 0.02, 0.001, 0)
        self._create_slider(sec2, "Glättungs-Buffer:",    "mouse.smoothing_buffer_size", 1, 20, 1, 1, use_int=True)
        self._create_slider(sec2, "Min Cutoff (1€-Filter):", "mouse.min_cutoff",      0.01, 5.0, 0.01, 2)
        self._create_slider(sec2, "Beta (1€-Filter):",    "mouse.beta",              0.0, 0.1, 0.001, 3)
        self._create_slider(sec2, "D-Cutoff:",            "mouse.d_cutoff",          0.1, 5.0, 0.1, 4)
        self._create_slider(sec2, "Pixel-Deadzone:",      "mouse.pixel_deadzone",    0, 30, 1, 5, use_int=True)
        self._create_slider(sec2, "Pause (s):",           "mouse.pause_duration",    0.0, 0.1, 0.001, 6)

        sec3 = self._section(f, "Optionen")
        self._create_checkbox(sec3, "X-Achse invertieren",  "mouse.invert_x",  0)
        self._create_checkbox(sec3, "Y-Achse invertieren",  "mouse.invert_y",  1)
        self._create_checkbox(sec3, "Failsafe aktivieren",  "mouse.failsafe",  2,
                              hint="Ecke = Stop")

    def create_camera_tab(self, notebook):
        f = self._scrollable_frame(notebook, "📷  Kamera")

        sec = self._section(f, "Gerät")
        self._create_spinbox(sec, "Kamera-ID:",   "camera.camera_id", 0, 10, 0)
        self._create_slider(sec, "Ziel-FPS:",     "camera.fps_target", 5, 60, 1, 1, use_int=True)

        sec2 = self._section(f, "Auflösung")
        self._create_entry(sec2, "Breite (px):",  "camera.width",  0, 8)
        self._create_entry(sec2, "Höhe (px):",    "camera.height", 1, 8)

        sec3 = self._section(f, "Optionen")
        self._create_checkbox(sec3, "Horizontal spiegeln", "camera.flip_horizontal", 0)

    def create_tracking_tab(self, notebook):
        f = self._scrollable_frame(notebook, "👁  Tracking")

        sec = self._section(f, "MediaPipe Face Mesh")
        self._create_spinbox(sec, "Max. Gesichter:",      "tracking.max_num_faces", 1, 5, 0)
        self._create_slider(sec, "Erkennungs-Konfidenz:", "tracking.min_detection_confidence", 0.1, 1.0, 0.05, 1)
        self._create_slider(sec, "Tracking-Konfidenz:",   "tracking.min_tracking_confidence",  0.1, 1.0, 0.05, 2)
        self._create_checkbox(sec, "Landmarks verfeinern (Iris)", "tracking.refine_landmarks", 3,
                              hint="Nötig für Iris-Tracking")
        self._create_checkbox(sec, "Statischer Bildmodus", "tracking.static_image_mode", 4)

    def create_calibration_tab(self, notebook):
        f = self._scrollable_frame(notebook, "🎯  Kalibrierung")

        sec = self._section(f, "Parameter")
        self._create_slider(sec, "Benötigte Frames:", "calibration.frames_required", 10, 120, 5, 0, use_int=True)
        self._create_slider(sec, "Verzögerung (ms):", "calibration.calibration_delay_ms", 0, 2000, 100, 1, use_int=True)

        sec2 = self._section(f, "Optionen")
        self._create_checkbox(sec2, "Fortschrittsbalken anzeigen",       "calibration.show_progress_bar",          0)
        self._create_checkbox(sec2, "Auto-Rekalibrierung bei Gesichtsverlust", "calibration.auto_recalibrate_on_face_lost", 1)

    def create_gestures_tab(self, notebook):
        f = self._scrollable_frame(notebook, "✋  Gesten")

        available_actions = self.config.get("available_actions") or [
            "left_click", "right_click", "double_click", "middle_click",
            "scroll_up", "scroll_down", "drag_toggle",
            "key_enter", "key_space", "key_escape",
            "key_left", "key_right", "key_up", "key_down", "disabled"
        ]

        gestures = [
            ("mouth_open",      "Mund öffnen"),
            ("mouth_wide_open", "Mund weit öffnen"),
            ("smile",           "Lächeln"),
            ("eyebrow_raise",   "Augenbraue hochziehen"),
            ("head_tilt_left",  "Kopf links neigen"),
            ("head_tilt_right", "Kopf rechts neigen"),
        ]

        for g_key, g_label in gestures:
            sec = self._section(f, g_label)

            # Enabled
            en_var = tk.BooleanVar()
            self.temp_values[f"gesture_actions.{g_key}.enabled"] = en_var
            row0, bg0 = self._row(sec, 0)
            cb = tk.Checkbutton(row0, text="Aktiviert", variable=en_var,
                                font=("Segoe UI", 10), bd=0, cursor="hand2")
            self._reg(lambda w=cb, k=bg0: w.configure(
                bg=self.c[k], fg=self.c["text"],
                selectcolor=self.c["check_active"],
                activebackground=self.c[k]))
            cb.pack(side=tk.LEFT, padx=12)

            # Aktion
            ac_var = tk.StringVar()
            self.temp_values[f"gesture_actions.{g_key}.action"] = ac_var
            row1, bg1 = self._row(sec, 1)
            self._label(row1, "Aktion:", bg1)
            combo = ttk.Combobox(row1, textvariable=ac_var,
                                 values=available_actions,
                                 state="readonly", width=18, font=("Segoe UI", 10))
            combo.pack(side=tk.LEFT, padx=8)

            # Schwellenwert
            th_var = tk.DoubleVar()
            self.temp_values[f"gesture_actions.{g_key}.threshold"] = th_var
            self._create_slider(sec, "Schwellenwert:", f"gesture_actions.{g_key}.threshold",
                                0.01, 0.2, 0.005, 2)
            # Cooldown
            self._create_slider(sec, "Cooldown (Frames):", f"gesture_actions.{g_key}.cooldown_frames",
                                1, 60, 1, 3, use_int=True)

    def create_hotkeys_tab(self, notebook):
        f = self._scrollable_frame(notebook, "⌨  Hotkeys")
        sec = self._section(f, "Tastenbelegung")

        hotkeys = [
            ("hotkeys.toggle_tracking", "Tracking ein/aus:"),
            ("hotkeys.recalibrate",     "Neu kalibrieren:"),
            ("hotkeys.toggle_preview",  "Vorschau ein/aus:"),
            ("hotkeys.exit",            "Beenden:"),
        ]
        for i, (key, label) in enumerate(hotkeys):
            self._create_entry(sec, label, key, i, width=8)

    def create_general_tab(self, notebook):
        f = self._scrollable_frame(notebook, "⚙  Allgemein")

        sec = self._section(f, "Anwendung")
        self._create_checkbox(sec, "Minimiert starten",            "general.start_minimized",    0)
        self._create_checkbox(sec, "In System-Tray minimieren",    "general.minimize_to_tray",   1)
        self._create_checkbox(sec, "Benachrichtigungen anzeigen",  "general.show_notifications", 2)
        self._create_checkbox(sec, "Tracking automatisch starten", "general.autostart_tracking", 3)

        sec2 = self._section(f, "Anzeige")
        self._create_checkbox(sec2, "Vorschau-Fenster anzeigen",   "gui.show_preview_window",  0)
        self._create_checkbox(sec2, "Debug-Infos anzeigen",        "gui.show_debug_info",      1)
        self._create_checkbox(sec2, "Face Landmarks anzeigen",     "gui.show_landmarks",       2)
        self._create_checkbox(sec2, "FPS anzeigen",                "gui.show_fps",             3)
        self._create_checkbox(sec2, "Steuerungs-Hinweise anzeigen","gui.show_controls_hint",   4)

        # Vorschau-Auflösung
        sec3 = self._section(f, "Vorschau-Auflösung")
        self._create_entry(sec3, "Breite (px):",  "gui.preview_width",  0, 6)
        self._create_entry(sec3, "Höhe (px):",    "gui.preview_height", 1, 6)

        # Theme (wird auch per Toggle gesetzt)
        sec4 = self._section(f, "Design")
        self.temp_values["gui.theme"] = tk.StringVar(value=self.theme_name)
        self._create_combobox(sec4, "Design-Modus:", "gui.theme",
                              ["light", "dark"], 0)

        sec5 = self._section(f, "Config")
        row, bg = self._row(sec5, 0)
        self._make_btn(row, "📤  Config exportieren", self.export_config, "neutral").pack(
            side=tk.LEFT, padx=12, pady=4)
        self._make_btn(row, "📥  Config importieren", self.import_config, "neutral").pack(
            side=tk.LEFT, padx=4, pady=4)

    # ─── Laden / Speichern ───────────────────────────────────────────────────

    def load_current_values(self):
        for key, var in self.temp_values.items():
            value = self.config.get(key)
            if value is None:
                continue
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            elif isinstance(var, tk.IntVar):
                var.set(int(value))
            elif isinstance(var, tk.DoubleVar):
                var.set(float(value))
            elif isinstance(var, tk.StringVar):
                var.set(str(value))

    def save_settings(self):
        try:
            for key, var in self.temp_values.items():
                if isinstance(var, tk.BooleanVar):
                    self.config.set(key, var.get())
                elif isinstance(var, (tk.IntVar, tk.DoubleVar)):
                    self.config.set(key, var.get())
                elif isinstance(var, tk.StringVar):
                    value = var.get()
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                    self.config.set(key, value)

            self.config.save_config()
            messagebox.showinfo("Gespeichert", "Einstellungen wurden gespeichert!")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")

    def reset_to_defaults(self):
        if messagebox.askyesno("Zurücksetzen", "Wirklich alle Einstellungen zurücksetzen?"):
            self.config.reset_to_defaults()
            self.load_current_values()
            messagebox.showinfo("Zurückgesetzt", "Einstellungen wurden zurückgesetzt!")

    def export_config(self):
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
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            if self.config.import_config(filepath):
                self.load_current_values()
                messagebox.showinfo("Erfolg", "Config wurde importiert!")
            else:
                messagebox.showerror("Fehler", "Import fehlgeschlagen!")