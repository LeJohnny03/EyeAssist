import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time

# --- KONFIGURATION ---
BLINK_THRESHOLD = 0.012  # Empfindlichkeit für Blinzeln
SMOOTHING_FACTOR = 0.1   # 0.1 = sehr träge (weniger Jitter), 0.9 = sehr schnell (viel Jitter)

# MediaPipe Init
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True, # WICHTIG: Das gibt uns die Iris-Punkte!
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Bildschirmgröße holen
screen_w, screen_h = pyautogui.size()

# Webcam
cap = cv2.VideoCapture(0)

# --- KALIBRIERUNGS-ZUSTAND ---
# 0: Oben-Links, 1: Oben-Rechts, 2: Unten-Rechts, 3: Unten-Links, 4: Mitte, 5: FERTIG
calib_step = 0 
calib_points = [
    (50, 50),                  # Oben Links
    (screen_w - 50, 50),       # Oben Rechts
    (screen_w - 50, screen_h - 50), # Unten Rechts
    (50, screen_h - 50),       # Unten Links
    (screen_w // 2, screen_h // 2)  # Mitte
]
calib_data = [] # Hier speichern wir die Augen-Werte für jeden Punkt

blinked = False
old_gaze_x, old_gaze_y = screen_w // 2, screen_h // 2 # Für Smoothing

def get_blink_ratio(landmarks, w, h):
    """Berechnet, ob das Auge offen oder zu ist."""
    # Linkes Auge Punkte (Oben/Unten)
    top = landmarks[159]
    bottom = landmarks[145]
    dist = math.dist((top.x, top.y), (bottom.x, bottom.y))
    return dist

def get_iris_position(landmarks):
    """
    Berechnet die relative Position der Iris innerhalb des Auges.
    Gibt Werte zwischen 0.0 und 1.0 zurück (ungefähr).
    """
    # Indizes für Linkes Auge:
    # Innerer Winkel: 33, Äußerer Winkel: 133
    # Iris Zentrum: 468
    
    inner = np.array([landmarks[33].x, landmarks[33].y])
    outer = np.array([landmarks[133].x, landmarks[133].y])
    iris = np.array([landmarks[468].x, landmarks[468].y])
    
    # Gesamte Augenbreite
    eye_width = np.linalg.norm(outer - inner)
    
    # Distanz Iris zu Innerem Winkel (horizontal)
    dist_to_inner = np.linalg.norm(iris - inner)
    
    # Wir vereinfachen hier stark: Wir nehmen nur die horizontale Relation
    # Vertikal ist mit Webcam extrem schwer wegen Augenlidern
    ratio_x = dist_to_inner / eye_width
    
    # Für Y nehmen wir Iris relativ zur Augenhöhe (Oben 159, Unten 145)
    top = np.array([landmarks[159].x, landmarks[159].y])
    bottom = np.array([landmarks[145].x, landmarks[145].y])
    eye_height = np.linalg.norm(bottom - top)
    
    # Distanz Iris zu oberem Lid
    dist_to_top = np.linalg.norm(iris - top)
    ratio_y = dist_to_top / eye_height

    return ratio_x, ratio_y

# Fenster erstellen und auf Vollbild setzen
cv2.namedWindow('Calibration', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('Calibration', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("Starte Kalibrierung... Drücke ESC zum Beenden.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    # Wir erstellen ein schwarzes Bild für das UI (Overlay)
    ui_frame = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
    
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        h_cam, w_cam, _ = frame.shape
        
        # 1. Blinzeln erkennen
        blink_ratio = get_blink_ratio(landmarks, w_cam, h_cam)
        
        # 2. Iris Position holen (Das sind unsere Rohdaten für den Blick)
        iris_x_ratio, iris_y_ratio = get_iris_position(landmarks)

        # --- LOGIK: KALIBRIERUNG ---
        if calib_step < 5:
            # Zeichne den Zielpunkt
            target_x, target_y = calib_points[calib_step]
            cv2.circle(ui_frame, (target_x, target_y), 20, (0, 0, 255), -1) # Roter Punkt
            cv2.putText(ui_frame, "Punkt anschauen & Blinzeln", (target_x - 100, target_y + 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            if blink_ratio < BLINK_THRESHOLD:
                if not blinked:
                    print(f"Punkt {calib_step} gespeichert: {iris_x_ratio:.3f}, {iris_y_ratio:.3f}")
                    calib_data.append((iris_x_ratio, iris_y_ratio))
                    blinked = True
                    # Kleines visuelles Feedback (grün aufleuchten)
                    cv2.circle(ui_frame, (target_x, target_y), 30, (0, 255, 0), -1)
                    cv2.waitKey(200) # Kurz warten für Feedback
                    calib_step += 1
            else:
                blinked = False

        # --- LOGIK: TRACKING (NACH DER KALIBRIERUNG) ---
        else:
            cv2.putText(ui_frame, "TRACKING MODUS (ESC beendet)", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Wir brauchen Min/Max Werte aus der Kalibrierung
            # X-Werte: Index 0 (Links) ist Min, Index 1 (Rechts) ist Max
            # Achtung: Weil gespiegelt und relativ:
            # Blick nach Links (auf Screen) = Iris ist nah am inneren Winkel (kleiner ratio)
            # Blick nach Rechts = Iris ist weg vom inneren Winkel (großer ratio)
            
            # Vereinfachte Extraktion der Grenzen aus den Kalibrierungsdaten:
            # Wir nehmen den Durchschnitt der linken Punkte als "Links-Grenze"
            calib_left_x = (calib_data[0][0] + calib_data[3][0]) / 2
            calib_right_x = (calib_data[1][0] + calib_data[2][0]) / 2
            
            calib_top_y = (calib_data[0][1] + calib_data[1][1]) / 2
            calib_bottom_y = (calib_data[2][1] + calib_data[3][1]) / 2

            # Mapping: Aktueller Iris-Wert -> Screen Koordinaten
            # Formel: (Aktuell - Min) / (Max - Min) * ScreenSize
            
            # X-Achse
            x_diff = calib_right_x - calib_left_x
            if x_diff == 0: x_diff = 0.001 # div/0 verhindern
            norm_x = (iris_x_ratio - calib_left_x) / x_diff
            gaze_x = int(norm_x * screen_w)
            
            # Y-Achse
            y_diff = calib_bottom_y - calib_top_y
            if y_diff == 0: y_diff = 0.001
            norm_y = (iris_y_ratio - calib_top_y) / y_diff
            gaze_y = int(norm_y * screen_h)

            # Glättung (Smoothing)
            gaze_x = int(old_gaze_x + (gaze_x - old_gaze_x) * SMOOTHING_FACTOR)
            gaze_y = int(old_gaze_y + (gaze_y - old_gaze_y) * SMOOTHING_FACTOR)
            old_gaze_x, old_gaze_y = gaze_x, gaze_y

            # Zeichne den geschätzten Blickpunkt (Grüner Kreis)
            cv2.circle(ui_frame, (gaze_x, gaze_y), 25, (0, 255, 0), 3)
            cv2.line(ui_frame, (gaze_x-10, gaze_y), (gaze_x+10, gaze_y), (0, 255, 0), 2)
            cv2.line(ui_frame, (gaze_x, gaze_y-10), (gaze_x, gaze_y+10), (0, 255, 0), 2)

    # UI und Kamerabild mischen (optional, hier zeigen wir nur das schwarze UI)
    cv2.imshow('Calibration', ui_frame)
    
    if cv2.waitKey(1) & 0xFF == 27: # ESC
        break

cap.release()
cv2.destroyAllWindows()