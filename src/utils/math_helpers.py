"""Mathematische Hilfsfunktionen für Tracking"""
import numpy as np
from collections import deque

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