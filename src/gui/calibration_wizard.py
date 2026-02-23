import tkinter as tk
from tkinter import ttk
import time
import numpy as np

from src.core.eye_tracker import Calibrator, EMAFilter, make_calib_points


class CalibrationWizard(tk.Toplevel):
    """
    Fullscreen Wizard:
    - zeigt 9 Targets
    - SPACE oder Button startet Capture (samples_per_point)
    - sammelt Samples aus latest_feats (vom MainWindow geliefert)
    - fit -> callback(on_done(calibrator, pred_filter, feat_filter))
    """

    def __init__(self, master, cfg: dict, screen_w: int, screen_h: int, get_latest_feats_fn, on_done, on_cancel):
        super().__init__(master)
        self.cfg = cfg
        self.sw, self.sh = int(screen_w), int(screen_h)
        self.get_latest_feats = get_latest_feats_fn
        self.on_done = on_done
        self.on_cancel = on_cancel

        self.attributes("-fullscreen", True)
        self.configure(bg="black")
        self.focus_force()

        self.margin = float(cfg["eyetracking"]["calib_margin"])
        self.samples_per_point = int(cfg["eyetracking"]["samples_per_point"])

        self.calib_points = make_calib_points(self.sw, self.sh, margin=self.margin)
        self.idx = 0

        self.collecting = False
        self.collected = 0
        self.last_collect_time = 0.0

        self.calibrator = Calibrator(ridge_lambda=cfg["eyetracking"]["ridge_lambda"])
        self.feat_filter = EMAFilter(alpha=cfg["eyetracking"]["feat_ema_alpha"])
        self.pred_filter = EMAFilter(alpha=cfg["eyetracking"]["pred_ema_alpha"])

        self._build_ui()
        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<space>", lambda e: self._start_collect())

        self._tick()

    def _build_ui(self):
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        top = ttk.Frame(self.canvas)
        self.info_var = tk.StringVar(value="Schau auf den Punkt und drücke SPACE oder 'Capture'.")
        self.progress_var = tk.StringVar(value="1/9")
        self.warn_var = tk.StringVar(value="")

        self.info_lbl = ttk.Label(top, textvariable=self.info_var)
        self.prog_lbl = ttk.Label(top, textvariable=self.progress_var)
        self.warn_lbl = ttk.Label(top, textvariable=self.warn_var, foreground="red")

        btns = ttk.Frame(top)
        self.capture_btn = ttk.Button(btns, text="Capture (SPACE)", command=self._start_collect)
        self.cancel_btn = ttk.Button(btns, text="Abbrechen (ESC)", command=self._cancel)

        self.info_lbl.grid(row=0, column=0, sticky="w")
        self.prog_lbl.grid(row=0, column=1, sticky="e", padx=(20, 0))
        self.warn_lbl.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        btns.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.capture_btn.grid(row=0, column=0, padx=(0, 10))
        self.cancel_btn.grid(row=0, column=1)

        self.canvas.create_window(30, 30, anchor="nw", window=top)

    def _draw_target(self, x, y, label):
        self.canvas.delete("target")
        r1, r2 = 28, 5
        self.canvas.create_oval(x - r1, y - r1, x + r1, y + r1, outline="yellow", width=3, tags="target")
        self.canvas.create_oval(x - r2, y - r2, x + r2, y + r2, fill="yellow", outline="", tags="target")
        self.canvas.create_text(x + 60, y - 20, text=label, fill="yellow", font=("Segoe UI", 24, "bold"), tags="target")

    def _start_collect(self):
        if self.collecting:
            return
        feats = self.get_latest_feats()
        if feats is None:
            self.warn_var.set("Kein Gesicht erkannt – bitte Licht/Position prüfen.")
            return
        self.warn_var.set("")
        self.collecting = True
        self.collected = 0
        self.last_collect_time = 0.0
        self.info_var.set("Sammle Samples… Blick stabil halten.")

    def _tick(self):
        if not self.winfo_exists():
            return

        tx, ty = self.calib_points[self.idx]
        self.progress_var.set(f"{self.idx + 1}/9")
        self._draw_target(tx, ty, f"{self.idx + 1}/9")

        if self.collecting:
            now = time.time()
            feats = self.get_latest_feats()
            if feats is not None and (now - self.last_collect_time) > 0.01:
                feats = self.feat_filter.update(feats)
                self.calibrator.add_sample(feats, np.array([tx, ty], dtype=np.float32))
                self.collected += 1
                self.last_collect_time = now
                self.info_var.set(f"Sammle Samples… {self.collected}/{self.samples_per_point}")

            if self.collected >= self.samples_per_point:
                self.collecting = False
                self.collected = 0
                self.idx += 1
                self.info_var.set("Schau auf den nächsten Punkt und drücke SPACE/Capture.")

                if self.idx >= len(self.calib_points):
                    ok = self.calibrator.fit()
                    if ok:
                        self._finish()
                        return
                    else:
                        self.warn_var.set("Fit fehlgeschlagen. Bitte erneut kalibrieren.")
                        self.idx = 0
                        self.calibrator.reset()

        self.after(10, self._tick)

    def _finish(self):
        self.on_done(self.calibrator, self.feat_filter, self.pred_filter)
        self.destroy()

    def _cancel(self):
        self.on_cancel()
        self.destroy()
