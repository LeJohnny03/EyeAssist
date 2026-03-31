"""Gemeinsame Farbpaletten für Hell/Dunkel-Modus"""

THEMES = {
    "light": {
        "bg":             "#f7f6f2",
        "surface":        "#ffffff",
        "surface2":       "#f3f0ec",
        "surface3":       "#e6e4df",
        "border":         "#d4d1ca",
        "text":           "#28251d",
        "text_muted":     "#7a7974",
        "text_faint":     "#bab9b4",
        "accent":         "#01696f",
        "accent_hover":   "#0c4e54",
        "accent_fg":      "#ffffff",
        "success":        "#437a22",
        "success_fg":     "#ffffff",
        "danger":         "#a12c7b",
        "danger_fg":      "#ffffff",
        "warning":        "#964219",
        "warning_fg":     "#ffffff",
        "neutral":        "#e6e4df",
        "neutral_fg":     "#28251d",
        "neutral_hover":  "#d4d1ca",
        "slider_trough":  "#dcd9d5",
        "check_active":   "#01696f",
        "tab_active":     "#ffffff",
        "tab_inactive":   "#f3f0ec",
        "status_ready":   "#437a22",
        "status_active":  "#01696f",
        "status_stopped": "#7a7974",
    },
    "dark": {
        "bg":             "#171614",
        "surface":        "#1c1b19",
        "surface2":       "#22211f",
        "surface3":       "#2d2c2a",
        "border":         "#393836",
        "text":           "#cdccca",
        "text_muted":     "#797876",
        "text_faint":     "#5a5957",
        "accent":         "#4f98a3",
        "accent_hover":   "#227f8b",
        "accent_fg":      "#171614",
        "success":        "#6daa45",
        "success_fg":     "#171614",
        "danger":         "#d163a7",
        "danger_fg":      "#171614",
        "warning":        "#bb653b",
        "warning_fg":     "#171614",
        "neutral":        "#2d2c2a",
        "neutral_fg":     "#cdccca",
        "neutral_hover":  "#393836",
        "slider_trough":  "#2d2c2a",
        "check_active":   "#4f98a3",
        "tab_active":     "#1c1b19",
        "tab_inactive":   "#141312",
        "status_ready":   "#6daa45",
        "status_active":  "#4f98a3",
        "status_stopped": "#797876",
    },
}


def apply_ttk_style(theme_name: str):
    """Wendet ttk-Style für das gewählte Theme an."""
    from tkinter import ttk
    c = THEMES[theme_name]
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("TNotebook",
                background=c["bg"], borderwidth=0, tabmargins=[0, 0, 0, 0])
    s.configure("TNotebook.Tab",
                background=c["tab_inactive"], foreground=c["text"],
                padding=[16, 8], font=("Segoe UI", 10), borderwidth=0)
    s.map("TNotebook.Tab",
          background=[("selected", c["tab_active"]), ("active", c["surface2"])],
          foreground=[("selected", c["accent"])])
    s.configure("TFrame",       background=c["surface"])
    s.configure("Flat.TFrame",  background=c["bg"])
    s.configure("TScrollbar",
                background=c["surface2"], troughcolor=c["bg"],
                borderwidth=0, arrowcolor=c["text_muted"])
    s.configure("TCombobox",
                fieldbackground=c["surface"], background=c["surface"],
                foreground=c["text"], selectbackground=c["accent"],
                selectforeground=c["accent_fg"], borderwidth=1)
    s.map("TCombobox",
          fieldbackground=[("readonly", c["surface"])],
          foreground=[("readonly", c["text"])])