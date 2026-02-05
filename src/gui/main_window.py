import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk

from src.core.tracker_engine import TrackerEngine
from src.core.mouse_controller import MouseController
from src.core.gesture_recognizer import GestureRecognizer
from src.utils.camera_helper import open_camera
from src.utils.config_manager import ConfigManager

from src.core.eye_tracker import compute_hybrid_features
from src.gui.calibration_wizard import CalibrationWizard


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Eyetracking state
        self.eye_calibrated = False
        self.eye_calibrator = None
        self.eye_feat_filter = None
        self.eye_pred_filter = None
        self.latest_eye_feats = None


        self.title("Head/Eye Mouse")
        self.geometry("1050x650")
        self.minsize(950, 600)

        self.cfg = ConfigManager.load_or_create_default()

        # Core components
        self.cap = open_camera(self.cfg["camera"]["index"])
        if self.cap is None:
            raise RuntimeError("Kamera konnte nicht geöffnet werden.")

        self.tracker = TrackerEngine(self.cfg)
        self.mouse = MouseController(self.cfg)
        self.gestures = GestureRecognizer(self.cfg)

        # UI state
        self._photo = None  # keep reference
        self._running = True

        self._build_ui()
        self._apply_cfg_to_ui()

        # start loop
        self.after(10, self._tick)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------
    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        root.columnconfigure(0, weight=2)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        # Left: Preview
        preview_frame = ttk.LabelFrame(root, text="Kamera Preview", padding=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        # Status bar under preview
        self.status_var = tk.StringVar(value="Bereit.")
        self.status_label = ttk.Label(preview_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        # Right: Controls + Settings
        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)

        # Quick Controls
        quick = ttk.LabelFrame(right, text="Steuerung", padding=10)
        quick.grid(row=0, column=0, sticky="ew")
        quick.columnconfigure(1, weight=1)

        self.enabled_var = tk.BooleanVar(value=True)
        enabled_cb = ttk.Checkbutton(
            quick,
            text="Computersteuerung aktiv",
            variable=self.enabled_var,
            command=self._on_toggle_enabled,
        )
        enabled_cb.grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(quick, text="Modus:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.mode_var = tk.StringVar(value="HEAD")
        self.mode_combo = ttk.Combobox(
            quick,
            textvariable=self.mode_var,
            values=["HEAD", "EYE"],
            state="readonly",
            width=10,
        )
        self.mode_combo.grid(row=1, column=1, sticky="w", pady=(8, 0))
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self._on_mode_change())

        self.stop_btn = ttk.Button(quick, text="Steuerung stoppen", command=self._stop_control)
        self.stop_btn.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.start_btn = ttk.Button(quick, text="Steuerung starten", command=self._start_control)
        self.start_btn.grid(row=2, column=1, sticky="ew", pady=(10, 0))
        
        self.calib_btn = ttk.Button(quick, text="Eyetracking kalibrieren", command=self._start_eyetracking_calibration)
        self.calib_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # Settings Notebook
        settings = ttk.LabelFrame(right, text="Settings", padding=10)
        settings.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        settings.rowconfigure(0, weight=1)
        settings.columnconfigure(0, weight=1)

        self.nb = ttk.Notebook(settings)
        self.nb.grid(row=0, column=0, sticky="nsew")

        self._tab_control = ttk.Frame(self.nb, padding=10)
        self._tab_blink = ttk.Frame(self.nb, padding=10)
        self._tab_gestures = ttk.Frame(self.nb, padding=10)

        self.nb.add(self._tab_control, text="Maus")
        self.nb.add(self._tab_blink, text="Blinzeln")
        self.nb.add(self._tab_gestures, text="Gesten")

        self._build_control_tab()
        self._build_blink_tab()
        self._build_gesture_tab()

        # Save button
        self.save_btn = ttk.Button(right, text="Settings speichern", command=self._save_settings)
        self.save_btn.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    def _build_control_tab(self):
        f = self._tab_control
        f.columnconfigure(1, weight=1)

        self.sensx_var = tk.DoubleVar()
        self.sensy_var = tk.DoubleVar()
        self.smoothing_var = tk.DoubleVar()
        self.gain_var = tk.DoubleVar()

        ttk.Label(f, text="Sensitivity X").grid(row=0, column=0, sticky="w")
        ttk.Scale(f, from_=0.5, to=6.0, variable=self.sensx_var, orient="horizontal").grid(row=0, column=1, sticky="ew")
        ttk.Label(f, textvariable=self.sensx_var).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(f, text="Sensitivity Y").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(f, from_=0.5, to=6.0, variable=self.sensy_var, orient="horizontal").grid(row=1, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(f, textvariable=self.sensy_var).grid(row=1, column=2, padx=(8, 0), pady=(8, 0))

        ttk.Label(f, text="Smoothing").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(f, from_=0.05, to=0.9, variable=self.smoothing_var, orient="horizontal").grid(row=2, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(f, textvariable=self.smoothing_var).grid(row=2, column=2, padx=(8, 0), pady=(8, 0))

        ttk.Label(f, text="Gain (Offset Boost)").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(f, from_=1.0, to=6.0, variable=self.gain_var, orient="horizontal").grid(row=3, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(f, textvariable=self.gain_var).grid(row=3, column=2, padx=(8, 0), pady=(8, 0))

    def _build_blink_tab(self):
        f = self._tab_blink
        f.columnconfigure(1, weight=1)

        self.blink_thr_var = tk.DoubleVar()
        self.blink_cooldown_var = tk.IntVar()
        self.blink_hyst_var = tk.DoubleVar()

        ttk.Label(f, text="Blink Threshold").grid(row=0, column=0, sticky="w")
        ttk.Scale(f, from_=0.005, to=0.03, variable=self.blink_thr_var, orient="horizontal").grid(row=0, column=1, sticky="ew")
        ttk.Label(f, textvariable=self.blink_thr_var).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(f, text="Cooldown Frames").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(f, from_=0, to=40, variable=self.blink_cooldown_var, orient="horizontal").grid(row=1, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(f, textvariable=self.blink_cooldown_var).grid(row=1, column=2, padx=(8, 0), pady=(8, 0))

        ttk.Label(f, text="Hysteresis").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(f, from_=0.0, to=0.02, variable=self.blink_hyst_var, orient="horizontal").grid(row=2, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(f, textvariable=self.blink_hyst_var).grid(row=2, column=2, padx=(8, 0), pady=(8, 0))

    def _build_gesture_tab(self):
        f = self._tab_gestures
        f.columnconfigure(1, weight=1)

        self.both_close_s_var = tk.DoubleVar()
        self.both_thr_var = tk.DoubleVar()

        ttk.Label(f, text="Beide Augen zu (Sekunden)").grid(row=0, column=0, sticky="w")
        ttk.Scale(f, from_=1.0, to=6.0, variable=self.both_close_s_var, orient="horizontal").grid(row=0, column=1, sticky="ew")
        ttk.Label(f, textvariable=self.both_close_s_var).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(f, text="Both-Eyes Threshold").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(f, from_=0.005, to=0.03, variable=self.both_thr_var, orient="horizontal").grid(row=1, column=1, sticky="ew", pady=(8, 0))
        ttk.Label(f, textvariable=self.both_thr_var).grid(row=1, column=2, padx=(8, 0), pady=(8, 0))

    # ---------- Apply / Save ----------
    def _apply_cfg_to_ui(self):
        self.enabled_var.set(bool(self.cfg["control"].get("enabled", True)))
        self.mode_var.set(self.cfg["control"].get("mode", "HEAD"))

        self.sensx_var.set(float(self.cfg["control"]["sensitivity_x"]))
        self.sensy_var.set(float(self.cfg["control"]["sensitivity_y"]))
        self.smoothing_var.set(float(self.cfg["control"]["smoothing"]))
        self.gain_var.set(float(self.cfg["control"]["gain"]))

        self.blink_thr_var.set(float(self.cfg["blink"]["threshold"]))
        self.blink_cooldown_var.set(int(self.cfg["blink"]["cooldown_frames"]))
        self.blink_hyst_var.set(float(self.cfg["blink"]["hysteresis"]))

        self.both_close_s_var.set(float(self.cfg["gestures"]["both_eyes_close_seconds"]))
        self.both_thr_var.set(float(self.cfg["gestures"]["both_eyes_threshold"]))

        self.mouse.set_enabled(self.enabled_var.get())
        self.mouse.set_mode(self.mode_var.get())

    def _save_settings(self):
        # Write UI vars back to cfg
        self.cfg["control"]["enabled"] = bool(self.enabled_var.get())
        self.cfg["control"]["mode"] = self.mode_var.get()

        self.cfg["control"]["sensitivity_x"] = float(self.sensx_var.get())
        self.cfg["control"]["sensitivity_y"] = float(self.sensy_var.get())
        self.cfg["control"]["smoothing"] = float(self.smoothing_var.get())
        self.cfg["control"]["gain"] = float(self.gain_var.get())

        self.cfg["blink"]["threshold"] = float(self.blink_thr_var.get())
        self.cfg["blink"]["cooldown_frames"] = int(self.blink_cooldown_var.get())
        self.cfg["blink"]["hysteresis"] = float(self.blink_hyst_var.get())

        self.cfg["gestures"]["both_eyes_close_seconds"] = float(self.both_close_s_var.get())
        self.cfg["gestures"]["both_eyes_threshold"] = float(self.both_thr_var.get())

        ConfigManager.save(self.cfg, ConfigManager.PATH)

        # Apply live
        self.mouse.cfg = self.cfg
        self.gestures.cfg = self.cfg
        self.mouse.set_enabled(self.enabled_var.get())
        self.mouse.set_mode(self.mode_var.get())

        self.status_var.set("Settings gespeichert & angewendet.")

    # ---------- Callbacks ----------
    def _on_toggle_enabled(self):
        self.mouse.set_enabled(self.enabled_var.get())
        state = "aktiv" if self.enabled_var.get() else "deaktiviert"
        self.status_var.set(f"Computersteuerung {state}.")

    def _on_mode_change(self):
        mode = self.mode_var.get()
        self.mouse.set_mode(mode)

        if mode == "EYE":
            # Kalibrierung erzwingen
            if not self._ensure_eye_ready():
                # bleibt in EYE ausgewählt, aber Steuerung läuft erst nach calib sinnvoll
                pass
            else:
                self.status_var.set("Eyetracking-Modus aktiv.")
        else:
            self.status_var.set("Headtracking-Modus aktiv.")


    def _stop_control(self):
        self.enabled_var.set(False)
        self._on_toggle_enabled()

    def _start_control(self):
        self.enabled_var.set(True)
        self._on_toggle_enabled()

    # ---------- Main Loop ----------
    def _tick(self):
        if not self._running:
            return

        frame = self.tracker.read_frame(self.cap)
        if frame is None:
            self.status_var.set("Kein Kamerabild.")
            self.after(50, self._tick)
            return

        track = self.tracker.process(frame)
        
        # Eyetracking feats aktualisieren, falls Face vorhanden
        self.latest_eye_feats = None
        if track.has_face and track.landmarks is not None:
            try:
                feats, _dbg = compute_hybrid_features(track.landmarks, track.frame_w, track.frame_h)
                self.latest_eye_feats = feats
            except Exception:
                self.latest_eye_feats = None

        # Events
        event = self.gestures.update(track)

        if event == "STOP_CONTROL":
            self._stop_control()
            self.status_var.set("Beide Augen 3s zu: Steuerung gestoppt (App läuft weiter).")

        # Steuerung: abhängig von Mode
        if track.has_face and self.enabled_var.get():
            if self.mode_var.get() == "HEAD":
                if track.nose_px:
                    mx, my = self.mouse.compute_mouse_position_head(track.nose_px, track.frame_w, track.frame_h)
                    self.mouse.move(mx, my)
            elif self.mode_var.get() == "EYE":
                if not self.eye_calibrated or self.eye_calibrator is None:
                    # Eyetracking ohne Kalibrierung: nicht bewegen
                    # (Wizard wird beim Umschalten gestartet)
                    pass
                else:
                    feats = self.latest_eye_feats
                    if feats is not None:
                        # optional: zusätzlich glätten (Wizard hat feat_filter schon genutzt, hier nochmal stabil)
                        if self.eye_feat_filter is not None:
                            feats = self.eye_feat_filter.update(feats)

                        pred = self.eye_calibrator.predict(feats)
                        if pred is not None:
                            if self.eye_pred_filter is not None:
                                pred = self.eye_pred_filter.update(pred)
                            px, py = float(pred[0]), float(pred[1])

                            # Screen clamp
                            try:
                                import pyautogui
                                sw, sh = pyautogui.size()
                            except Exception:
                                sw, sh = 1920, 1080

                            px = max(0, min(sw - 1, px))
                            py = max(0, min(sh - 1, py))

                            self.mouse.move(px, py)

        if event == "LEFT_CLICK":
            self.mouse.left_click()

        # Preview render (OpenCV BGR -> Tk RGB)
        # Optional: Debug Text ins Frame malen
        if self.cfg["ui"]["debug_overlay"]:
            lx = self.gestures.last_left_eye_dist
            rx = self.gestures.last_right_eye_dist
            msg = f"L:{lx:.3f}  R:{rx:.3f}" if (lx is not None and rx is not None) else "No eye data"
            cv2.putText(frame, msg, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            if not self.enabled_var.get():
                cv2.putText(frame, "CONTROL OFF", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            if self.mode_var.get() == "EYE":
                cv2.putText(frame, "MODE: EYE (TODO)", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)

        # Auto-fit: skaliere auf Preview-Label Größe (ohne krassen Aufwand)
        pw = max(self.preview_label.winfo_width(), 1)
        ph = max(self.preview_label.winfo_height(), 1)
        img = img.resize((pw, ph))

        self._photo = ImageTk.PhotoImage(image=img)
        self.preview_label.configure(image=self._photo)

        self.after(10, self._tick)

    def on_close(self):
        self._running = False
        try:
            self.cap.release()
        except Exception:
            pass
        try:
            self.tracker.close()
        except Exception:
            pass
        self.destroy()

    def _start_eyetracking_calibration(self):
        # Screen size (für Targets)
        try:
            import pyautogui
            sw, sh = pyautogui.size()
        except Exception:
            sw, sh = 1920, 1080

        def get_latest_feats():
            return self.latest_eye_feats

        def on_done(calibrator, feat_filter, pred_filter):
            self.eye_calibrator = calibrator
            self.eye_feat_filter = feat_filter
            self.eye_pred_filter = pred_filter
            self.eye_calibrated = True
            self.status_var.set("Eyetracking: Kalibrierung abgeschlossen. Du kannst jetzt EYE benutzen.")

        def on_cancel():
            self.status_var.set("Eyetracking: Kalibrierung abgebrochen.")

        self.status_var.set("Eyetracking: Kalibrierung gestartet (Fullscreen).")
        CalibrationWizard(self, self.cfg, sw, sh, get_latest_feats, on_done, on_cancel)

    def _ensure_eye_ready(self) -> bool:
        if self.eye_calibrated and self.eye_calibrator is not None:
            return True
        self.status_var.set("Eyetracking benötigt Kalibrierung – starte Wizard…")
        self._start_eyetracking_calibration()
        return False
