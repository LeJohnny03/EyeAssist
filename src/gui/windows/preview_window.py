"""Vorschau-Fenster (Platzhalter)"""
import tkinter as tk

class PreviewWindow:
    """Zeigt Kamera-Vorschau (optional)"""
    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.title("Kamera-Vorschau")
        self.root.geometry("640x480")

        label = tk.Label(
            self.root,
            text="Vorschau-Fenster\n(Wird über OpenCV angezeigt)",
            font=("Arial", 14)
        )
        label.pack(expand=True)