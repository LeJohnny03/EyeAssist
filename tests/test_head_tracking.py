import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math

# --- KONFIGURATION ---
# Empfindlichkeit: Höher = Maus bewegt sich schneller bei kleiner Kopfbewegung
SENSITIVITY_X = 2.0  
SENSITIVITY_Y = 2.0

# Glättung: Wert zwischen 0.1 (sehr träge/weich) und 0.9 (sehr direkt/zittrig)
SMOOTHING = 0.3

# Blinzel-Einstellungen
BLINK_THRESHOLD = 0.014  # Schwelle für "Auge zu"
BLINK_COOLDOWN = 15      # Frames warten nach einem Klick (gegen Doppel-Klicks)

# PyAutoGUI Sicherheitseinstellungen
pyautogui.FAILSAFE = False # Erlaubt Maus in die Ecken (Vorsicht!)
pyautogui.PAUSE = 0        # Keine künstliche Verzögerung

# --- SETUP ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)
screen_w, screen_h = pyautogui.size()

# Variablen für Glättung
prev_mouse_x, prev_mouse_y = screen_w // 2, screen_h // 2
curr_mouse_x, curr_mouse_y = screen_w // 2, screen_h // 2

# Variablen für Blinzeln
blink_counter = 0
blink_detected = False

print("Head-Mouse gestartet. ESC zum Beenden.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    # Spiegeln, damit links auch links ist
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    frame_h, frame_w, _ = frame.shape

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark

        # --- 1. MAUS BEWEGUNG (NASE) ---
        # Nasenspitze ist Landmark 4
        nose = landmarks[4]
        
        # Koordinaten der Nase im Kamerabild (0 bis frame_w)
        nose_x = int(nose.x * frame_w)
        nose_y = int(nose.y * frame_h)

        # Wir nutzen die Mitte des Kamerabildes als "Nullpunkt"
        # Wenn Nase in der Mitte -> Maus in der Mitte
        # Offset berechnen (Wie weit ist Nase von der Mitte weg?)
        offset_x = nose_x - (frame_w // 2)
        offset_y = nose_y - (frame_h // 2)

        # Mapping auf Bildschirmkoordinaten mit Sensitivität
        # Formel: ScreenMitte + (Offset * Scaling * Sensitivity)
        # Wir skalieren das Offset hoch, damit man nicht den Kopf verrenken muss
        mapped_x = (screen_w // 2) + (offset_x * SENSITIVITY_X * (screen_w / frame_w) * 3)
        mapped_y = (screen_h // 2) + (offset_y * SENSITIVITY_Y * (screen_h / frame_h) * 3)

        # Grenzen setzen (Clipping), damit Maus nicht rausfliegt
        mapped_x = np.clip(mapped_x, 0, screen_w)
        mapped_y = np.clip(mapped_y, 0, screen_h)

        # Glättung anwenden (Linear Interpolation)
        curr_mouse_x = prev_mouse_x + (mapped_x - prev_mouse_x) * SMOOTHING
        curr_mouse_y = prev_mouse_y + (mapped_y - prev_mouse_y) * SMOOTHING

        # Maus bewegen
        pyautogui.moveTo(curr_mouse_x, curr_mouse_y)
        
        # Werte für nächsten Frame speichern
        prev_mouse_x, prev_mouse_y = curr_mouse_x, curr_mouse_y


        # --- 2. KLICKEN (LINKES AUGE BLINZELN) ---
        # Auge Punkte (Oben 159, Unten 145)
        left_eye_top = landmarks[159]
        left_eye_bottom = landmarks[145]
        
        # Einfache vertikale Distanz
        eye_dist = math.dist((left_eye_top.x, left_eye_top.y), 
                             (left_eye_bottom.x, left_eye_bottom.y))

        # Visuelles Feedback für Auge im Kamerabild
        cv2.putText(frame, f"Eye: {eye_dist:.3f}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        if blink_counter > 0:
            blink_counter -= 1
        
        if eye_dist < BLINK_THRESHOLD and blink_counter == 0:
            if not blink_detected:
                pyautogui.click()
                blink_detected = True
                blink_counter = BLINK_COOLDOWN # Cooldown starten
                cv2.putText(frame, "CLICK!", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        else:
            if eye_dist > BLINK_THRESHOLD + 0.005: # Hysterese (muss deutlich offen sein zum Reset)
                blink_detected = False

        # Nase im Bild einzeichnen (als Feedback)
        cv2.circle(frame, (nose_x, nose_y), 5, (0, 255, 255), -1)
        # Zentrum einzeichnen
        cv2.circle(frame, (frame_w // 2, frame_h // 2), 3, (200, 200, 200), -1)

    cv2.imshow('Head Mouse', frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()