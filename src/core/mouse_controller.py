import numpy as np

try:
    import pyautogui
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except Exception:
    HAS_PYAUTOGUI = False


class MouseController:
    """
    - Mapping Nase->Screen
    - enable/disable Computersteuerung
    - Mode: HEAD oder EYE (EYE später)
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.control_enabled = bool(cfg["control"].get("enabled", True))
        self.mode = cfg["control"].get("mode", "HEAD")

        self.screen_w, self.screen_h = (0, 0)
        if HAS_PYAUTOGUI:
            self.screen_w, self.screen_h = pyautogui.size()

        self.prev_x = self.screen_w // 2
        self.prev_y = self.screen_h // 2

    def set_enabled(self, enabled: bool):
        self.control_enabled = bool(enabled)

    def set_mode(self, mode: str):
        self.mode = mode

    def compute_mouse_position_head(self, nose_px: tuple[int, int], frame_w: int, frame_h: int) -> tuple[float, float]:
        if not HAS_PYAUTOGUI:
            return (0.0, 0.0)

        nose_x, nose_y = nose_px
        offset_x = nose_x - (frame_w // 2)
        offset_y = nose_y - (frame_h // 2)

        sens_x = self.cfg["control"]["sensitivity_x"]
        sens_y = self.cfg["control"]["sensitivity_y"]
        smoothing = self.cfg["control"]["smoothing"]
        gain = self.cfg["control"]["gain"]

        mapped_x = (self.screen_w // 2) + (offset_x * sens_x * (self.screen_w / frame_w) * gain)
        mapped_y = (self.screen_h // 2) + (offset_y * sens_y * (self.screen_h / frame_h) * gain)

        mapped_x = float(np.clip(mapped_x, 0, self.screen_w))
        mapped_y = float(np.clip(mapped_y, 0, self.screen_h))

        curr_x = self.prev_x + (mapped_x - self.prev_x) * smoothing
        curr_y = self.prev_y + (mapped_y - self.prev_y) * smoothing

        self.prev_x, self.prev_y = curr_x, curr_y
        return curr_x, curr_y

    def move(self, x: float, y: float):
        if self.control_enabled and HAS_PYAUTOGUI:
            pyautogui.moveTo(x, y)

    def left_click(self):
        if self.control_enabled and HAS_PYAUTOGUI:
            pyautogui.click()
