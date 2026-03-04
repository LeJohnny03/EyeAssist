"""Mathematische Hilfsfunktionen für Tracking"""
import numpy as np
import time
import math
from collections import deque

class LowPassFilter:
    """Einfacher Tiefpassfilter (intern für 1€-Filter)"""
    def __init__(self, cutoff):
        self.cutoff = cutoff
        self._y = None

    def _alpha(self, dt):
        tau = 1.0 / (2.0 * math.pi * self.cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x, dt):
        if self._y is None:
            self._y = x
        else:
            alpha = self._alpha(dt)
            self._y = alpha * x + (1.0 - alpha) * self._y
        return self._y

    def last_value(self):
        return self._y

    def reset(self):
        self._y = None


class OneEuroFilter:
    """1€-Filter für skalare Werte.

    Passt die Cutoff-Frequenz dynamisch an die Signalgeschwindigkeit an:
    - langsame Bewegung  → niedrige Cutoff → stärker geglättet (weniger Rauschen)
    - schnelle Bewegung  → hohe Cutoff    → weniger Glättung  (weniger Lag)

    Parameter:
        freq:      Abtastrate in Hz (Schätzwert, wird durch Zeitstempel überschrieben)
        mincutoff: Minimale Cutoff-Frequenz in Hz (höher = mehr Rauschen bei Stille)
        beta:      Geschwindigkeitskoeffizient  (höher = weniger Lag bei Bewegung)
        dcutoff:   Cutoff für den Ableitungsfilter in Hz
    """
    def __init__(self, freq=30.0, mincutoff=1.0, beta=0.007, dcutoff=1.0):
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self._x_filter = LowPassFilter(mincutoff)
        self._dx_filter = LowPassFilter(dcutoff)
        self._last_time = None

    def filter(self, x, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        if self._last_time is None:
            dt = 1.0 / self.freq
        else:
            dt = timestamp - self._last_time
            if dt <= 0:
                dt = 1.0 / self.freq
        self._last_time = timestamp

        prev_x = self._x_filter.last_value()
        if prev_x is None:
            prev_x = x

        dx = (x - prev_x) / dt
        edx = self._dx_filter.filter(dx, dt)

        cutoff = self.mincutoff + self.beta * abs(edx)
        self._x_filter.cutoff = cutoff

        return self._x_filter.filter(x, dt)

    def reset(self):
        self._x_filter = LowPassFilter(self.mincutoff)
        self._dx_filter = LowPassFilter(self.dcutoff)
        self._last_time = None


class OneEuroFilter2D:
    """Glättet 2D-Bewegungsdaten mit dem 1€-Filter.

    Drop-in-Ersatz für MovementSmoother mit identischem Interface.
    """
    def __init__(self, freq=30.0, mincutoff=1.0, beta=0.007, dcutoff=1.0):
        self._filter_x = OneEuroFilter(freq, mincutoff, beta, dcutoff)
        self._filter_y = OneEuroFilter(freq, mincutoff, beta, dcutoff)
        self._smoothed_x = 0.0
        self._smoothed_y = 0.0

    def add_point(self, x, y):
        """Fügt neuen Punkt hinzu und filtert ihn sofort"""
        t = time.time()
        self._smoothed_x = self._filter_x.filter(x, t)
        self._smoothed_y = self._filter_y.filter(y, t)

    def get_smoothed(self):
        """Gibt geglättete Koordinaten zurück"""
        return self._smoothed_x, self._smoothed_y

    def clear(self):
        """Setzt Filter zurück (z.B. nach Kalibrierung)"""
        self._filter_x.reset()
        self._filter_y.reset()
        self._smoothed_x = 0.0
        self._smoothed_y = 0.0


class MovementSmoother:
    """Glättet Bewegungsdaten mit Rolling Average"""
    def __init__(self, buffer_size=5):
        self.buffer_x = deque(maxlen=buffer_size)
        self.buffer_y = deque(maxlen=buffer_size)

    def add_point(self, x, y):
        """Fügt neuen Punkt hinzu"""
        self.buffer_x.append(x)
        self.buffer_y.append(y)

    def get_smoothed(self):
        """Gibt geglättete Koordinaten zurück"""
        if len(self.buffer_x) == 0:
            return 0, 0
        return np.mean(self.buffer_x), np.mean(self.buffer_y)

    def clear(self):
        """Löscht Buffer"""
        self.buffer_x.clear()
        self.buffer_y.clear()

def calculate_distance_2d(point1, point2):
    """Berechnet euklidische Distanz zwischen zwei 2D-Punkten"""
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def calculate_vertical_distance(point1, point2):
    """Berechnet vertikale Distanz zwischen zwei Punkten"""
    return abs(point1[1] - point2[1])

def map_to_screen(value, input_range, output_range):
    """Mappt Wert von einem Bereich auf einen anderen"""
    input_min, input_max = input_range
    output_min, output_max = output_range

    normalized = (value - input_min) / (input_max - input_min)
    mapped = output_min + normalized * (output_max - output_min)

    return max(output_min, min(output_max, mapped))

def clamp(value, min_value, max_value):
    """Begrenzt Wert auf Min/Max-Bereich"""
    return max(min_value, min(max_value, value))