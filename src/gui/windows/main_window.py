"""Hauptfenster der GUI-Anwendung – modernes Design"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from gui.theme import THEMES, apply_ttk_style
from gui.windows.settings_window import SettingsWindow
from gui.windows.gesture_mapping_window import GestureMappingWindow
from core.application import HybridTrackingApp


class MainWindow:
    """Hauptfenster der Anwendung"""

    def __init__(self, config):
        self.config = config
        self.theme_name = config.get("gui.theme") or "light"
        self.c = THEMES[self.theme_name]

        self.root = tk.Tk()
        self.root.title("EyeAssist")
        self.root.geometry("460x520")
        self.root.resizable(False, False)

        self.tracking_app = None
        self.tracking_thread = None
        self.is_tracking = False
        self.settings_window = None
        self.gesture_window = None

        self._widgets = []  # Theme-Refresh-Funktionen

        apply_ttk_style(self.theme_name)
        self._build_ui()
        self._refresh_all()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        if self.config.get("general.autostart_tracking"):
            self.root.after(500, self._start_tracking)

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _reg(self, fn):
        self._widgets.append(fn)

    def _refresh_all(self):
        for fn in self._widgets:
            fn()

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.c = THEMES[self.theme_name]
        self.config.set("gui.theme", self.theme_name)
        apply_ttk_style(self.theme_name)
        self._refresh_all()
        # Theme-Icon aktualisieren
        self._theme_btn.config(text="☀️" if self.theme_name == "dark" else "🌙")

    # ─── UI-Aufbau ───────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(bg=self.c["bg"])
        self._reg(lambda: self.root.configure(bg=self.c["bg"]))

        # ── Header ──────────────────────────────────────────────────────────
        header = tk.Frame(self.root, height=72)
        self._reg(lambda w=header: w.configure(bg=self.c["surface"]))
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Logo + Titel
        logo_lbl = tk.Label(header, text="👁", font=("Segoe UI", 22))
        self._reg(lambda w=logo_lbl: w.configure(
            bg=self.c["surface"], fg=self.c["accent"]))
        logo_lbl.pack(side=tk.LEFT, padx=(20, 8), pady=14)

        title_col = tk.Frame(header)
        self._reg(lambda w=title_col: w.configure(bg=self.c["surface"]))
        title_col.pack(side=tk.LEFT, pady=14)

        title_lbl = tk.Label(title_col, text="EyeAssist",
                             font=("Segoe UI Semibold", 15), anchor="w")
        self._reg(lambda w=title_lbl: w.configure(
            bg=self.c["surface"], fg=self.c["text"]))
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(title_col, text="Hybrid Tracking Mouse Control",
                           font=("Segoe UI", 9), anchor="w")
        self._reg(lambda w=sub_lbl: w.configure(
            bg=self.c["surface"], fg=self.c["text_muted"]))
        sub_lbl.pack(anchor="w")

        # Theme-Toggle
        self._theme_btn = tk.Button(
            header,
            text="🌙" if self.theme_name == "light" else "☀️",
            font=("Segoe UI", 14), bd=0, relief=tk.FLAT,
            padx=12, command=self.toggle_theme, cursor="hand2"
        )
        self._reg(lambda w=self._theme_btn: w.configure(
            bg=self.c["surface"], fg=self.c["text"],
            activebackground=self.c["surface2"],
            activeforeground=self.c["accent"]))
        self._theme_btn.pack(side=tk.RIGHT, padx=12)

        # Trennlinie
        self._sep(self.root)

        # ── Inhalt ───────────────────────────────────────────────────────────
        body = tk.Frame(self.root, padx=20, pady=16)
        self._reg(lambda w=body: w.configure(bg=self.c["bg"]))
        body.pack(fill=tk.BOTH, expand=True)

        # Status-Karte
        self._build_status_card(body)

        # Tracking-Button
        self._build_tracking_button(body)

        # Aktions-Grid
        self._build_action_grid(body)

        # Hotkey-Hinweis
        self._build_hotkey_hint(body)

        # ── Footer ───────────────────────────────────────────────────────────
        self._sep(self.root)
        footer = tk.Frame(self.root, height=36)
        self._reg(lambda w=footer: w.configure(bg=self.c["surface"]))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        footer.pack_propagate(False)

        footer_lbl = tk.Label(footer, text="v1.0  •  Powered by MediaPipe",
                              font=("Segoe UI", 8))
        self._reg(lambda w=footer_lbl: w.configure(
            bg=self.c["surface"], fg=self.c["text_faint"]))
        footer_lbl.pack(side=tk.LEFT, padx=16, pady=9)

    def _sep(self, parent):
        s = tk.Frame(parent, height=1)
        self._reg(lambda w=s: w.configure(bg=self.c["border"]))
        s.pack(fill=tk.X)

    def _build_status_card(self, parent):
        card = tk.Frame(parent, pady=14, padx=16)
        self._reg(lambda w=card: w.configure(bg=self.c["surface"],
                                              highlightbackground=self.c["border"],
                                              highlightthickness=1))
        card.pack(fill=tk.X, pady=(0, 14))

        top = tk.Frame(card)
        self._reg(lambda w=top: w.configure(bg=self.c["surface"]))
        top.pack(fill=tk.X)

        section_lbl = tk.Label(top, text="STATUS",
                               font=("Segoe UI", 8, "bold"))
        self._reg(lambda w=section_lbl: w.configure(
            bg=self.c["surface"], fg=self.c["accent"]))
        section_lbl.pack(side=tk.LEFT)

        # Status-Dot + Text
        dot_row = tk.Frame(card)
        self._reg(lambda w=dot_row: w.configure(bg=self.c["surface"]))
        dot_row.pack(fill=tk.X, pady=(8, 0))

        self._status_dot = tk.Label(dot_row, text="●", font=("Segoe UI", 18))
        self._reg(lambda w=self._status_dot: w.configure(bg=self.c["surface"]))
        self._status_dot.pack(side=tk.LEFT)

        status_col = tk.Frame(dot_row)
        self._reg(lambda w=status_col: w.configure(bg=self.c["surface"]))
        status_col.pack(side=tk.LEFT, padx=10)

        self._status_lbl = tk.Label(status_col, text="Bereit",
                                    font=("Segoe UI Semibold", 13))
        self._reg(lambda w=self._status_lbl: w.configure(bg=self.c["surface"]))
        self._status_lbl.pack(anchor="w")

        self._status_sub = tk.Label(status_col,
                                    text="Tracking ist gestoppt.",
                                    font=("Segoe UI", 9))
        self._reg(lambda w=self._status_sub: w.configure(
            bg=self.c["surface"], fg=self.c["text_muted"]))
        self._status_sub.pack(anchor="w")

        self._set_status("ready")

    def _set_status(self, state: str):
        """state: 'ready' | 'active' | 'stopped'"""
        mapping = {
            "ready":   ("Bereit",  "Tracking ist gestoppt.",          "status_ready"),
            "active":  ("Aktiv",   "Tracking läuft.",                 "status_active"),
            "stopped": ("Gestoppt","Tracking wurde beendet.",         "status_stopped"),
        }
        text, sub, color_key = mapping[state]
        color = self.c[color_key]
        self._status_dot.config(fg=color)
        self._status_lbl.config(text=text, fg=color)
        self._status_sub.config(text=sub)

    def _build_tracking_button(self, parent):
        self._track_btn = tk.Button(
            parent, text="▶  Tracking starten",
            font=("Segoe UI Semibold", 12),
            bd=0, relief=tk.FLAT, pady=14,
            command=self._toggle_tracking, cursor="hand2"
        )
        self._reg(lambda w=self._track_btn: w.configure(
            bg=self.c["accent"], fg=self.c["accent_fg"],
            activebackground=self.c["accent_hover"],
            activeforeground=self.c["accent_fg"]
        ) if not self.is_tracking else w.configure(
            bg=self.c["danger"], fg=self.c["danger_fg"],
            activebackground=self.c["danger"],
            activeforeground=self.c["danger_fg"]
        ))
        self._track_btn.pack(fill=tk.X, pady=(0, 14))

    def _build_action_grid(self, parent):
        grid = tk.Frame(parent)
        self._reg(lambda w=grid: w.configure(bg=self.c["bg"]))
        grid.pack(fill=tk.X, pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        buttons = [
            ("⚙  Einstellungen",   self._open_settings,        0, 0),
            ("✋  Gesten-Mapping",  self._open_gesture_mapping,  0, 1),
            ("📹  Vorschau",        self._toggle_preview,        1, 0),
            ("🔄  Rekalibrieren",   self._recalibrate,           1, 1),
        ]

        self._recal_btn = None

        for text, cmd, r, c_idx in buttons:
            btn = tk.Button(
                grid, text=text,
                font=("Segoe UI", 10),
                bd=0, relief=tk.FLAT, pady=10,
                command=cmd, cursor="hand2"
            )
            self._reg(lambda w=btn: w.configure(
                bg=self.c["surface2"], fg=self.c["text"],
                activebackground=self.c["neutral_hover"],
                activeforeground=self.c["text"]
            ))
            btn.grid(row=r, column=c_idx,
                     sticky="ew",
                     padx=(0, 5) if c_idx == 0 else (5, 0),
                     pady=(0, 6))

            if text.startswith("🔄"):
                self._recal_btn = btn
                btn.config(state=tk.DISABLED)
                self._reg(lambda w=btn: w.configure(fg=self.c["text_faint"])
                          if str(w["state"]) == "disabled" else None)

    def _build_hotkey_hint(self, parent):
        hk = self.config.get("hotkeys.toggle_tracking") or "F9"
        rec = self.config.get("hotkeys.recalibrate") or "F10"
        ex = self.config.get("hotkeys.exit") or "F12"

        hint_lbl = tk.Label(
            parent,
            text=f"{hk} Tracking  •  {rec} Kalibrieren  •  {ex} Beenden",
            font=("Segoe UI", 8)
        )
        self._reg(lambda w=hint_lbl: w.configure(
            bg=self.c["bg"], fg=self.c["text_faint"]))
        hint_lbl.pack(anchor="center")

    # ─── Tracking ────────────────────────────────────────────────────────────

    def _toggle_tracking(self):
        if not self.is_tracking:
            self._start_tracking()
        else:
            self._stop_tracking()

    def _start_tracking(self):
        try:
            self.tracking_app = HybridTrackingApp(self.config)
            self.tracking_thread = threading.Thread(
                target=self._run_tracking, daemon=True)
            self.tracking_thread.start()
            self.is_tracking = True
            self._track_btn.config(
                text="■  Tracking stoppen",
                bg=self.c["danger"], fg=self.c["danger_fg"],
                activebackground=self.c["danger"])
            self._set_status("active")
            if self._recal_btn:
                self._recal_btn.config(state=tk.NORMAL)
                self._reg(lambda w=self._recal_btn: w.configure(fg=self.c["text"]))
                self._refresh_all()
        except Exception as e:
            messagebox.showerror("Fehler", f"Tracking konnte nicht gestartet werden:\n{e}")

    def _run_tracking(self):
        try:
            self.tracking_app.start()
        except Exception as e:
            print(f"Tracking-Fehler: {e}")
            self.root.after(0, self._stop_tracking)

    def _stop_tracking(self):
        if self.tracking_app:
            self.tracking_app.stop()
            self.tracking_app = None
        self.is_tracking = False
        self._track_btn.config(
            text="▶  Tracking starten",
            bg=self.c["accent"], fg=self.c["accent_fg"],
            activebackground=self.c["accent_hover"])
        self._set_status("stopped")
        if self._recal_btn:
            self._recal_btn.config(state=tk.DISABLED)

    def _recalibrate(self):
        if self.tracking_app:
            self.tracking_app.recalibrate()
            messagebox.showinfo("Rekalibrierung", "Kalibrierung wurde zurückgesetzt!")

    # ─── Fenster ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        if not self.settings_window or not self.settings_window.root.winfo_exists():
            self.settings_window = SettingsWindow(self.config, self.root)

    def _open_gesture_mapping(self):
        if not self.gesture_window or not self.gesture_window.root.winfo_exists():
            self.gesture_window = GestureMappingWindow(self.config, self.root)

    def _toggle_preview(self):
        cur = self.config.get("gui.show_preview_window", True)
        self.config.set("gui.show_preview_window", not cur)
        self.config.save_config()
        state = "aktiviert" if not cur else "deaktiviert"
        messagebox.showinfo("Vorschau",
                            f"Vorschau-Fenster {state}.\nStarte Tracking neu zum Übernehmen.")

    def _on_closing(self):
        if self.is_tracking:
            if not messagebox.askyesno("Tracking aktiv",
                                       "Tracking läuft noch. Wirklich beenden?"):
                return
            self._stop_tracking()
        self.root.destroy()

    def run(self):
        self.root.mainloop()