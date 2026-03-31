"""Gesten-Mapping-Fenster – modernes Design"""
import tkinter as tk
from tkinter import ttk, messagebox
from gui.theme import THEMES, apply_ttk_style


class GestureMappingWindow:
    """Fenster zum Konfigurieren von Gesten-zu-Aktion-Mappings"""

    GESTURE_LABELS = {
        "mouth_open":      "Mund öffnen",
        "mouth_wide_open": "Mund weit öffnen",
        "smile":           "Lächeln",
        "eyebrow_raise":   "Augenbraue hochziehen",
        "head_tilt_left":  "Kopf links neigen",
        "head_tilt_right": "Kopf rechts neigen",
    }
    ACTION_LABELS = {
        "left_click":   "Linksklick",
        "right_click":  "Rechtsklick",
        "double_click": "Doppelklick",
        "middle_click": "Mittelklick",
        "scroll_up":    "Hoch scrollen",
        "scroll_down":  "Runter scrollen",
        "drag_toggle":  "Drag umschalten",
        "key_enter":    "Enter",
        "key_space":    "Leertaste",
        "key_escape":   "Escape",
        "key_left":     "Pfeil links",
        "key_right":    "Pfeil rechts",
        "key_up":       "Pfeil hoch",
        "key_down":     "Pfeil runter",
        "disabled":     "Deaktiviert",
    }

    def __init__(self, config, parent):
        self.config = config
        self.theme_name = config.get("gui.theme") or "light"
        self.c = THEMES[self.theme_name]

        self.root = tk.Toplevel(parent)
        self.root.title("EyeAssist – Gesten-Mapping")
        self.root.geometry("680x520")
        self.root.resizable(True, True)
        self.root.minsize(560, 400)

        self.gesture_widgets = {}
        self._widgets = []

        apply_ttk_style(self.theme_name)
        self._build_ui()
        self.load_gestures()

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _reg(self, fn):
        self._widgets.append(fn)
        fn()

    def _refresh_all(self):
        for fn in self._widgets:
            fn()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(bg=self.c["bg"])
        self._reg(lambda: self.root.configure(bg=self.c["bg"]))

        # Header
        header = tk.Frame(self.root, height=60)
        self._reg(lambda w=header: w.configure(bg=self.c["surface"]))
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(header, text="✋  Gesten-Mapping",
                         font=("Segoe UI Semibold", 13), anchor="w", padx=20)
        self._reg(lambda w=title: w.configure(
            bg=self.c["surface"], fg=self.c["text"]))
        title.pack(side=tk.LEFT, pady=14)

        info = tk.Label(header,
                        text="Aktiviere Gesten und weise Aktionen zu",
                        font=("Segoe UI", 9), anchor="e", padx=20)
        self._reg(lambda w=info: w.configure(
            bg=self.c["surface"], fg=self.c["text_muted"]))
        info.pack(side=tk.RIGHT, pady=14)

        sep = tk.Frame(self.root, height=1)
        self._reg(lambda w=sep: w.configure(bg=self.c["border"]))
        sep.pack(fill=tk.X)

        # Scroll-Container
        container = tk.Frame(self.root)
        self._reg(lambda w=container: w.configure(bg=self.c["bg"]))
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        canvas = tk.Canvas(container, bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._reg(lambda w=canvas: w.configure(bg=self.c["bg"]))

        self._inner = tk.Frame(canvas)
        self._reg(lambda w=self._inner: w.configure(bg=self.c["bg"]))
        win_id = canvas.create_window((0, 0), window=self._inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        self._inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", _resize)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(
                            int(-1 * e.delta / 120), "units"))

        # Footer
        sep2 = tk.Frame(self.root, height=1)
        self._reg(lambda w=sep2: w.configure(bg=self.c["border"]))
        sep2.pack(fill=tk.X)

        btn_bar = tk.Frame(self.root)
        self._reg(lambda w=btn_bar: w.configure(bg=self.c["bg"]))
        btn_bar.pack(fill=tk.X, padx=16, pady=10)

        self._make_btn(btn_bar, "✕  Abbrechen",
                       self.root.destroy, "neutral").pack(side=tk.RIGHT, padx=(8, 0))
        self._make_btn(btn_bar, "✓  Speichern",
                       self.save_gestures, "accent").pack(side=tk.RIGHT)

    def _make_btn(self, parent, text, cmd, style):
        b = tk.Button(parent, text=text, command=cmd,
                      font=("Segoe UI", 10), bd=0, relief=tk.FLAT,
                      padx=16, pady=8, cursor="hand2")
        if style == "accent":
            self._reg(lambda w=b: w.configure(
                bg=self.c["accent"], fg=self.c["accent_fg"],
                activebackground=self.c["accent_hover"],
                activeforeground=self.c["accent_fg"]))
        else:
            self._reg(lambda w=b: w.configure(
                bg=self.c["neutral"], fg=self.c["neutral_fg"],
                activebackground=self.c["neutral_hover"],
                activeforeground=self.c["text"]))
        return b

    # ─── Gesten-Karten ───────────────────────────────────────────────────────

    def load_gestures(self):
        gesture_actions = self.config.get_section("gesture_actions")
        available_actions = self.config.get("available_actions") or list(
            self.ACTION_LABELS.keys())
        action_display = [self.ACTION_LABELS.get(a, a) for a in available_actions]
        rev_map = {self.ACTION_LABELS.get(a, a): a for a in available_actions}

        for g_id, g_data in gesture_actions.items():
            self._build_gesture_card(g_id, g_data, action_display, rev_map)

    def _build_gesture_card(self, g_id, g_data, action_display, rev_map):
        """Erstellt eine Gesten-Karte im modernen Stil."""
        card = tk.Frame(self._inner, pady=0)
        self._reg(lambda w=card: w.configure(bg=self.c["bg"]))
        card.pack(fill=tk.X, pady=(0, 8))

        # Karten-Header (Gestenname + Enabled-Toggle)
        ch = tk.Frame(card, pady=8, padx=14)
        self._reg(lambda w=ch: w.configure(
            bg=self.c["surface"],
            highlightbackground=self.c["border"],
            highlightthickness=1))
        ch.pack(fill=tk.X)

        en_var = tk.BooleanVar(value=g_data.get("enabled", False))
        cb = tk.Checkbutton(ch, variable=en_var,
                            font=("Segoe UI Semibold", 11), bd=0, cursor="hand2",
                            text=self.GESTURE_LABELS.get(g_id, g_id))
        self._reg(lambda w=cb: w.configure(
            bg=self.c["surface"], fg=self.c["text"],
            selectcolor=self.c["check_active"],
            activebackground=self.c["surface"],
            activeforeground=self.c["accent"]))
        cb.pack(side=tk.LEFT)

        # Karten-Body
        body = tk.Frame(card, padx=14, pady=8)
        self._reg(lambda w=body: w.configure(bg=self.c["surface2"]))
        body.pack(fill=tk.X)

        # Zeile 1: Aktion
        row1 = tk.Frame(body)
        self._reg(lambda w=row1: w.configure(bg=self.c["surface2"]))
        row1.pack(fill=tk.X, pady=(0, 6))

        lbl1 = tk.Label(row1, text="Aktion:", font=("Segoe UI", 10), width=18, anchor="w")
        self._reg(lambda w=lbl1: w.configure(
            bg=self.c["surface2"], fg=self.c["text_muted"]))
        lbl1.pack(side=tk.LEFT)

        ac_var = tk.StringVar(
            value=self.ACTION_LABELS.get(g_data.get("action", "disabled"), "Deaktiviert"))
        combo = ttk.Combobox(row1, textvariable=ac_var, values=action_display,
                             state="readonly", width=22, font=("Segoe UI", 10))
        combo.pack(side=tk.LEFT)

        # Zeile 2: Schwellenwert
        row2 = tk.Frame(body)
        self._reg(lambda w=row2: w.configure(bg=self.c["surface2"]))
        row2.pack(fill=tk.X, pady=(0, 4))

        lbl2 = tk.Label(row2, text="Schwellenwert:", font=("Segoe UI", 10), width=18, anchor="w")
        self._reg(lambda w=lbl2: w.configure(
            bg=self.c["surface2"], fg=self.c["text_muted"]))
        lbl2.pack(side=tk.LEFT)

        th_var = tk.DoubleVar(value=g_data.get("threshold", 0.03))
        th_val_lbl = tk.Label(row2, font=("Segoe UI Semibold", 10), width=6)
        self._reg(lambda w=th_val_lbl: w.configure(
            bg=self.c["surface2"], fg=self.c["accent"]))
        th_val_lbl.pack(side=tk.RIGHT, padx=(0, 4))

        def _upd_th(*_):
            th_val_lbl.config(text=f"{th_var.get():.3f}")
        th_var.trace_add("write", _upd_th)
        _upd_th()

        slider = tk.Scale(row2, from_=0.005, to=0.2, resolution=0.005,
                          orient=tk.HORIZONTAL, variable=th_var,
                          showvalue=False, length=200, bd=0, highlightthickness=0)
        self._reg(lambda w=slider: w.configure(
            bg=self.c["surface2"], fg=self.c["accent"],
            troughcolor=self.c["slider_trough"],
            activebackground=self.c["accent_hover"]))
        slider.pack(side=tk.LEFT, padx=(0, 4))

        # Zeile 3: Cooldown
        row3 = tk.Frame(body)
        self._reg(lambda w=row3: w.configure(bg=self.c["surface2"]))
        row3.pack(fill=tk.X)

        lbl3 = tk.Label(row3, text="Cooldown (Frames):", font=("Segoe UI", 10), width=18, anchor="w")
        self._reg(lambda w=lbl3: w.configure(
            bg=self.c["surface2"], fg=self.c["text_muted"]))
        lbl3.pack(side=tk.LEFT)

        cd_var = tk.IntVar(value=g_data.get("cooldown_frames", 15))
        cd_val_lbl = tk.Label(row3, font=("Segoe UI Semibold", 10), width=6)
        self._reg(lambda w=cd_val_lbl: w.configure(
            bg=self.c["surface2"], fg=self.c["accent"]))
        cd_val_lbl.pack(side=tk.RIGHT, padx=(0, 4))

        def _upd_cd(*_):
            cd_val_lbl.config(text=str(cd_var.get()))
        cd_var.trace_add("write", _upd_cd)
        _upd_cd()

        cd_slider = tk.Scale(row3, from_=1, to=60, resolution=1,
                             orient=tk.HORIZONTAL, variable=cd_var,
                             showvalue=False, length=200, bd=0, highlightthickness=0)
        self._reg(lambda w=cd_slider: w.configure(
            bg=self.c["surface2"], fg=self.c["accent"],
            troughcolor=self.c["slider_trough"],
            activebackground=self.c["accent_hover"]))
        cd_slider.pack(side=tk.LEFT, padx=(0, 4))

        self.gesture_widgets[g_id] = {
            "enabled":   en_var,
            "action":    ac_var,
            "threshold": th_var,
            "cooldown":  cd_var,
            "rev_map":   rev_map,
        }

    # ─── Speichern ───────────────────────────────────────────────────────────

    def save_gestures(self):
        try:
            gestures = {}
            for g_id, w in self.gesture_widgets.items():
                ac_display = w["action"].get()
                ac_id = w["rev_map"].get(ac_display, ac_display)
                gestures[g_id] = {
                    "enabled":        w["enabled"].get(),
                    "action":         ac_id,
                    "threshold":      round(w["threshold"].get(), 4),
                    "cooldown_frames": w["cooldown"].get(),
                }
            self.config.update_section("gesture_actions", gestures)
            self.config.save_config()
            messagebox.showinfo("Gespeichert", "Gesten-Mapping wurde gespeichert!")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")