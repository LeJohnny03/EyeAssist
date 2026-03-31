"""Logging-Mechanismus für objektive Metriken – Studienarbeit Kap. 3.6.1

Abgedeckte Metriken:
  1. Time-to-Target (TTT): Zeitspanne zwischen Ziel-Erscheinen und Linksklick
  2. System-Latenz / Framerate: Durchlaufzeit Capture→Injection in ms + FPS
"""
import csv
import time
import os
from datetime import datetime


class MetricsLogger:
    """Schreibt TTT- und Framerate-Metriken in eine CSV-Datei."""

    CSV_HEADER = [
        "timestamp_iso",        # Absoluter Zeitstempel (ISO-8601)
        "event_type",           # 'frame' | 'target_appeared' | 'click_registered'
        "frame_latency_ms",     # Capture→Injection Latenz in ms  (nur bei 'frame')
        "fps",                  # Gleitender FPS-Wert             (nur bei 'frame')
        "cursor_delta_x",       # Cursor-Delta in x               (nur bei 'frame')
        "cursor_delta_y",       # Cursor-Delta in y               (nur bei 'frame')
        "x",                    # X-Koordinate des Cursors          (nur bei 'frame')
        "y",                    # Y-Koordinate des Cursors          (nur bei 'frame')
        "ttt_ms",               # Time-to-Target in ms  (nur bei 'click_registered')
    ]

    def __init__(self, output_dir: str = "metrics", enabled: bool = True):
        self.enabled = enabled
        self._target_appear_time: float | None = None
        self._frame_start_time:   float | None = None
        self._last_frame_time:    float | None = None
        self._fps_alpha = 0.1          # EMA-Gewicht für gleitenden FPS
        self._fps_ema:  float = 0.0

        if not self.enabled:
            self._file = None
            self._writer = None
            return

        os.makedirs(output_dir, exist_ok=True)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"metrics_{session_ts}.csv")

        self._file   = open(filepath, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.CSV_HEADER)
        self._writer.writeheader()
        self._file.flush()

    # ------------------------------------------------------------------
    # Metrik 2: System-Latenz & Framerate
    # ------------------------------------------------------------------

    def frame_start(self) -> None:
        """Muss zu Beginn jeder Frame-Verarbeitung aufgerufen werden."""
        self._frame_start_time = time.perf_counter()

    def frame_end(self, cursor_delta_x: float = 0.0,
                  cursor_delta_y: float = 0.0, x: float = 0.0, y: float = 0.0) -> None:
        """Muss am Ende der Frame-Verarbeitung aufgerufen werden.

        Parameters
        ----------
        cursor_delta_x/y : Head-Delta zur Referenzposition (aus MouseController).
        x/y : X- und Y-Koordinaten des Cursors.
        """
        if not self.enabled or self._frame_start_time is None:
            return

        now = time.perf_counter()
        latency_ms = (now - self._frame_start_time) * 1000.0

        # Gleitender FPS-Durchschnitt via Exponential Moving Average
        if self._last_frame_time is not None:
            instant_fps = 1.0 / max(now - self._last_frame_time, 1e-9)
            self._fps_ema = (
                instant_fps if self._fps_ema == 0.0
                else (1 - self._fps_alpha) * self._fps_ema
                     + self._fps_alpha * instant_fps
            )
        self._last_frame_time = now

        self._write_row(
            event_type="frame",
            frame_latency_ms=round(latency_ms, 3),
            fps=round(self._fps_ema, 2),
            cursor_delta_x=round(cursor_delta_x, 6),
            cursor_delta_y=round(cursor_delta_y, 6),
            x=round(x, 2),
            y=round(y, 2),
        )

    # ------------------------------------------------------------------
    # Metrik 1: Time-to-Target (TTT)
    # ------------------------------------------------------------------

    def target_appeared(self) -> None:
        """Markiert den Zeitpunkt, zu dem ein Ziel sichtbar wird."""
        if not self.enabled:
            return
        self._target_appear_time = time.perf_counter()
        self._write_row(event_type="target_appeared")
        
    def has_active_target(self) -> bool:
        """True solange das Target noch nicht geklickt wurde."""
        return self._target_appear_time is not None

    def click_registered(self, x: float = 0.0, y: float = 0.0) -> None:
        """Markiert einen Linksklick und berechnet TTT."""
        if not self.enabled:
            return

        ttt_ms: float | None = None
        if self._target_appear_time is not None:
            ttt_ms = (time.perf_counter() - self._target_appear_time) * 1000.0
            self._target_appear_time = None   # Reset nach Registrierung

        self._write_row(
            event_type="click_registered",
            x=round(x, 2),
            y=round(y, 2),
            ttt_ms=round(ttt_ms, 3) if ttt_ms is not None else None,
        )

    # ------------------------------------------------------------------
    # Interne Hilfsmethoden
    # ------------------------------------------------------------------

    def _write_row(self, **kwargs) -> None:
        if not self.enabled or self._writer is None:
            return
        row = {col: "" for col in self.CSV_HEADER}
        row["timestamp_iso"] = datetime.now().isoformat(timespec="milliseconds")
        row.update(kwargs)
        self._writer.writerow(row)
        self._file.flush()

    def get_fps(self) -> float:
        """Gibt den aktuellen EMA-FPS-Wert zurück (z. B. für das Overlay)."""
        return round(self._fps_ema, 1)

    def close(self) -> None:
        """Schließt die CSV-Datei."""
        if self._file:
            self._file.close()
            self._file = None
            self._writer = None
