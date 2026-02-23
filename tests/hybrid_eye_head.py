import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time

# -------------------
# KONFIGURATION
# -------------------
# Grundempfindlichkeit
SENSITIVITY_X = 2.0
SENSITIVITY_Y = 2.0

# Glättung (LERP)
SMOOTHING = 0.28  # 0.2-0.4 oft gut

# Deadzone (in Pixeln im Kamerabild) – verhindert Zittern
DEADZONE_PX = 12

# Beschleunigung: je größer der Offset, desto schneller (macht "große Wege" angenehm)
# exponent >1 => schneller bei großen Ausschlägen
ACCEL_EXP = 1.35

# Maximaler Maus-Schritt pro Frame (gegen Ausreißer)
MAX_STEP_PX = 65

# Blink-Klick
BLINK_THRESHOLD = 0.014
BLINK_COOLDOWN_FRAMES = 15
BLINK_HYST = 0.005  # wie bei dir

# Optional: Dwell-Click zusätzlich (wenn du willst)
ENABLE_DWELL = False
DWELL_TIME = 0.9         # Sekunden
DWELL_RADIUS_PX = 25     # Maus muss innerhalb Radius bleiben
DWELL_COOLDOWN = 1.0     # Sekunden

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# -------------------
# SETUP
# -------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)
screen_w, screen_h = pyautogui.size()

# Startposition
curr_mouse = np.array([screen_w / 2, screen_h / 2], dtype=np.float32)
prev_mouse = curr_mouse.copy()

# Neutralpunkt (recenter)
neutral_nose = None  # (x,y) in Bildkoordinaten

# Blink-States
blink_counter = 0
blink_detected = False

# Dwell-States
dwell_anchor = None
dwell_since = None
last_dwell_click = 0.0

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def apply_deadzone(offset_xy, deadzone_px):
    ox, oy = offset_xy
    if abs(ox) < deadzone_px:
        ox = 0.0
    else:
        ox = ox - math.copysign(deadzone_px, ox)
    if abs(oy) < deadzone_px:
        oy = 0.0
    else:
        oy = oy - math.copysign(deadzone_px, oy)
    return np.array([ox, oy], dtype=np.float32)

def accel_curve(offset_xy, exp_):
    # non-linear acceleration; preserve direction
    ox, oy = offset_xy
    ax = math.copysign(abs(ox) ** exp_, ox)
    ay = math.copysign(abs(oy) ** exp_, oy)
    return np.array([ax, ay], dtype=np.float32)

print("Hybrid HeadMouse gestartet.")
print("Tasten: ESC=Beenden | N=Recenter | D=Dwell Toggle")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    frame_h, frame_w, _ = frame.shape
    now = time.time()

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark

        # -------------------
        # 1) HEAD MOVE (NOSE)
        # -------------------
        nose = landmarks[4]
        nose_x = float(nose.x * frame_w)
        nose_y = float(nose.y * frame_h)
        nose_xy = np.array([nose_x, nose_y], dtype=np.float32)

        # Neutral setzen, wenn noch nicht vorhanden
        if neutral_nose is None:
            neutral_nose = np.array([frame_w / 2, frame_h / 2], dtype=np.float32)

        # Offset relativ zum Neutralpunkt (nicht zwingend Bildmitte!)
        offset = nose_xy - neutral_nose

        # Deadzone
        offset = apply_deadzone(offset, DEADZONE_PX)

        # Beschleunigungskurve
        offset = accel_curve(offset, ACCEL_EXP)

        # Map auf Screen: Skalierung Kamerabild -> Screen
        mapped_x = (screen_w / 2) + (offset[0] * SENSITIVITY_X * (screen_w / frame_w) * 3.0)
        mapped_y = (screen_h / 2) + (offset[1] * SENSITIVITY_Y * (screen_h / frame_h) * 3.0)

        mapped = np.array([mapped_x, mapped_y], dtype=np.float32)
        mapped[0] = clamp(mapped[0], 0, screen_w - 1)
        mapped[1] = clamp(mapped[1], 0, screen_h - 1)

        # LERP smoothing
        smoothed = prev_mouse + (mapped - prev_mouse) * SMOOTHING

        # Clamp step per frame (gegen Sprünge)
        step = smoothed - prev_mouse
        n = float(np.linalg.norm(step))
        if n > MAX_STEP_PX:
            step = step / max(n, 1e-6) * MAX_STEP_PX
            smoothed = prev_mouse + step

        curr_mouse = smoothed
        prev_mouse = curr_mouse.copy()

        pyautogui.moveTo(int(curr_mouse[0]), int(curr_mouse[1]))

        # -------------------
        # 2) CLICK (BLINK)
        # -------------------
        left_eye_top = landmarks[159]
        left_eye_bottom = landmarks[145]
        eye_dist = math.dist(
            (left_eye_top.x, left_eye_top.y),
            (left_eye_bottom.x, left_eye_bottom.y)
        )

        cv2.putText(frame, f"Eye: {eye_dist:.3f}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if blink_counter > 0:
            blink_counter -= 1

        if eye_dist < BLINK_THRESHOLD and blink_counter == 0:
            if not blink_detected:
                pyautogui.click()
                blink_detected = True
                blink_counter = BLINK_COOLDOWN_FRAMES
                cv2.putText(frame, "CLICK!", (30, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        else:
            if eye_dist > BLINK_THRESHOLD + BLINK_HYST:
                blink_detected = False

        # -------------------
        # 3) OPTIONAL: DWELL CLICK (Eye-intent alternative)
        # -------------------
        if ENABLE_DWELL:
            if dwell_anchor is None:
                dwell_anchor = curr_mouse.copy()
                dwell_since = now

            if np.linalg.norm(curr_mouse - dwell_anchor) <= DWELL_RADIUS_PX:
                if dwell_since is None:
                    dwell_since = now
                dur = now - dwell_since
                cv2.putText(frame, f"Dwell: {dur:.2f}s", (30, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

                if dur >= DWELL_TIME and (now - last_dwell_click) >= DWELL_COOLDOWN:
                    pyautogui.click()
                    last_dwell_click = now
                    dwell_anchor = None
                    dwell_since = None
            else:
                dwell_anchor = curr_mouse.copy()
                dwell_since = now

        # Visual feedback
        cv2.circle(frame, (int(nose_x), int(nose_y)), 5, (0, 255, 255), -1)
        cv2.circle(frame, (int(neutral_nose[0]), int(neutral_nose[1])), 4, (200, 200, 200), -1)

    cv2.putText(frame, "ESC quit | N recenter | D dwell toggle", (30, frame.shape[0]-20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2)

    cv2.imshow("Hybrid HeadMouse (Improved)", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == 27:  # ESC
        break
    if key == ord('n') or key == ord('N'):
        # recenter to current nose position (comfortable neutral)
        if results.multi_face_landmarks:
            neutral_nose = np.array([nose_x, nose_y], dtype=np.float32)
    if key == ord('d') or key == ord('D'):
        ENABLE_DWELL = not ENABLE_DWELL

cap.release()
cv2.destroyAllWindows()
