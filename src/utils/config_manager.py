"""Erweiterte Konfigurationsverwaltung mit JSON-Persistenz"""
import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.default_config = {
            # === Kamera-Einstellungen ===
            'camera': {
                'camera_id': 0,
                'width': 640,
                'height': 480,
                'flip_horizontal': True,
                'fps_target': 30
            },

            # === MediaPipe Tracking ===
            'tracking': {
                'max_num_faces': 1,
                'refine_landmarks': True,
                'min_detection_confidence': 0.5,
                'min_tracking_confidence': 0.5,
                'static_image_mode': False,
                'pose_mincutoff': 1.5,
                'pose_beta': 0.05,
                'pose_dcutoff': 1.0
            },

            # === Kalibrierung ===
            'calibration': {
                'frames_required': 30,
                'auto_recalibrate_on_face_lost': False,
                'show_progress_bar': True,
                'calibration_delay_ms': 0
            },

            # === Maussteuerung ===
            'mouse': {
                'sensitivity_x': 5,
                'sensitivity_y': 6,
                'movement_threshold': 0.002,
                'smoothing_buffer_size': 3,
                'invert_x': False,
                'invert_y': False,
                'failsafe': False,
                'pause_duration': 0.001,
                'min_cutoff': 1.0,
                'beta': 0.007,
                'd_cutoff': 1.0,
                'pixel_deadzone': 5,
                'max_angle': 30.0
            },

            # === Gesten-Mapping ===
            'gesture_actions': {
                'mouth_open': {
                    'enabled': True,
                    'action': 'left_click',
                    'threshold': 0.03,
                    'cooldown_frames': 15
                },
                'mouth_wide_open': {
                    'enabled': False,
                    'action': 'right_click',
                    'threshold': 0.05,
                    'cooldown_frames': 15
                },
                'smile': {
                    'enabled': False,
                    'action': 'double_click',
                    'threshold': 0.04,
                    'cooldown_frames': 20
                },
                'eyebrow_raise': {
                    'enabled': False,
                    'action': 'scroll_up',
                    'threshold': 0.02,
                    'cooldown_frames': 5
                },
                'head_tilt_left': {
                    'enabled': False,
                    'action': 'key_left',
                    'threshold': 0.15,
                    'cooldown_frames': 10
                },
                'head_tilt_right': {
                    'enabled': False,
                    'action': 'key_right',
                    'threshold': 0.15,
                    'cooldown_frames': 10
                }
            },

            # === Verfügbare Aktionen ===
            'available_actions': [
                'left_click',
                'right_click',
                'double_click',
                'middle_click',
                'scroll_up',
                'scroll_down',
                'drag_toggle',
                'key_enter',
                'key_space',
                'key_escape',
                'key_left',
                'key_right',
                'key_up',
                'key_down',
                'disabled'
            ],

            # === GUI / Overlay ===
            'gui': {
                'window_name': 'Head Tracking Mouse Control',
                'show_preview_window': True,
                'preview_width': 640,
                'preview_height': 480,
                'show_debug_info': True,
                'show_landmarks': True,
                'show_fps': True,
                'show_controls_hint': True,
                'theme': 'light'
            },

            # === Overlay-Farben (BGR) ===
            'colors': {
                'calibrating': [0, 255, 255],
                'calibrated': [0, 255, 0],
                'error': [0, 0, 255],
                'landmarks': [0, 255, 0],
                'click_indicator': [0, 0, 255],
                'text': [255, 255, 255],
                'progress_bar_bg': [50, 50, 50],
                'progress_bar_fg': [0, 255, 255]
            },

            # === Tastenbelegung ===
            'hotkeys': {
                'toggle_tracking': 'F9',
                'recalibrate': 'F10',
                'toggle_preview': 'F11',
                'exit': 'F12'
            },

            # === Allgemeine Einstellungen ===
            'general': {
                'start_minimized': False,
                'minimize_to_tray': True,
                'show_notifications': True,
                'autostart_tracking': False,
                'language': 'de'
            }
        }
        self.config = self.load_config()

    def load_config(self):
        """Lädt Konfiguration aus JSON-Datei"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    merged = self._deep_merge(self.default_config, loaded_config)
                    self.config = merged
                    self.save_config() 
                    return merged
            except Exception as e:
                print(f"Fehler beim Laden der Config: {e}")
                return self._deep_copy(self.default_config)
        else:
            # Erstelle Config-Datei mit Defaults
            self.save_config()
        return self._deep_copy(self.default_config)

    def save_config(self):
        """Speichert Konfiguration in JSON-Datei"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern der Config: {e}")
            return False

    def get(self, key_path, default=None):
        """Gibt Konfigurationswert zurück (verschachtelt: 'camera.width')"""
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path, value):
        """Setzt Konfigurationswert (verschachtelt: 'camera.width')"""
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def get_section(self, section):
        """Gibt gesamte Config-Sektion zurück"""
        return self.config.get(section, {})

    def update_section(self, section, data):
        """Aktualisiert gesamte Sektion"""
        if section in self.config:
            self.config[section].update(data)
        else:
            self.config[section] = data

    def reset_to_defaults(self):
        """Setzt Konfiguration auf Standardwerte zurück"""
        self.config = self._deep_copy(self.default_config)
        self.save_config()

    def export_config(self, filepath):
        """Exportiert Config in andere Datei"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except:
            return False

    def import_config(self, filepath):
        """Importiert Config aus Datei"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
                self.config = self._deep_merge(self.default_config, imported)
                self.save_config()
            return True
        except:
            return False

    def _deep_merge(self, default, override):
        """Merged zwei verschachtelte Dictionaries"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _deep_copy(self, obj):
        """Erstellt tiefe Kopie"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj