import json
import os


DEFAULT_CONFIG = {
    "camera": {
        "index": 0,
        "flip": True
    },
    "tracking": {
        "min_detection_confidence": 0.5,
        "min_tracking_confidence": 0.5
    },
    "control": {
        "sensitivity_x": 2.0,
        "sensitivity_y": 2.0,
        "smoothing": 0.3,
        "gain": 3.0,
        "mode": "HEAD",
        "enabled": True
    },
    "blink": {
        "threshold": 0.014,
        "cooldown_frames": 15,
        "hysteresis": 0.005
    },
    "gestures": {
        "both_eyes_close_seconds": 3.0,
        "both_eyes_threshold": 0.012  # oft etwas niedriger als blink threshold, feinjustierbar
    },
    "ui": {
        "window_name": "Head/Eye Mouse",
        "debug_overlay": True,
        "show_landmarks": False
    },
    "eyetracking": {
        "calib_margin": 0.12,
        "samples_per_point": 30,
        "feat_ema_alpha": 0.25,
        "pred_ema_alpha": 0.20,
        "ridge_lambda": 1e-2
    },
}



class ConfigManager:
    PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

    @classmethod
    def load_or_create_default(cls) -> dict:
        path = os.path.abspath(cls.PATH)

        if not os.path.exists(path):
            cls.save(DEFAULT_CONFIG, path)
            return DEFAULT_CONFIG

        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            # Fallback bei kaputter Datei
            cls.save(DEFAULT_CONFIG, path)
            return DEFAULT_CONFIG

        # Minimaler Merge: fehlende Keys ergänzen
        return _deep_merge(DEFAULT_CONFIG, cfg)

    @staticmethod
    def save(cfg: dict, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
