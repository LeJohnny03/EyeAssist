import cv2
import mediapipe as mp
from pynput.mouse import Button, Controller
import math

# --- KONFIGURATION ---
BLINK_THRESHOLD = 0.015  # Schwellenwert: Wie weit muss das Auge geschlossen sein? 
                         # (Kleiner = man muss fester zukneifen)
                         # Spiel hier etwas herum, falls es zu empfindlich ist.

# Initialisiere Maus-Controller
mouse = Controller()

# MediaPipe Setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Webcam starten (0 ist meistens die Standard-Kamera)
cap = cv2.VideoCapture(0)

# Variable, um Dauer-Klicks zu verhindern
blink_detected = False 

print("Programm gestartet. Drücke 'ESC' zum Beenden.")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Kamera nicht gefunden.")
        break

    # Bild spiegeln (wirkt natürlicher) und Farben für MediaPipe anpassen
    image = cv2.flip(image, 1)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Gesichtserkennung ausführen
    results = face_mesh.process(rgb_image)

    # Bild wieder zurückwandeln für Anzeige
    image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    h, w, _ = image.shape

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            # --- HIER PASSIERT DIE MAGIE ---
            
            # Wir holen uns die Punkte für das LINKE Auge
            # Punkt 159 = Oberes Lid, Punkt 145 = Unteres Lid
            top_lid = face_landmarks.landmark[159]
            bottom_lid = face_landmarks.landmark[145]

            # Umrechnen von relativen (0.0-1.0) in absolute Pixel-Koordinaten
            top_point = (int(top_lid.x * w), int(top_lid.y * h))
            bottom_point = (int(bottom_lid.x * w), int(bottom_lid.y * h))

            # Distanz berechnen (Euklidische Distanz)
            # Wir nutzen hier eine vereinfachte vertikale Distanz
            vertical_distance = math.dist(top_point, bottom_point)
            
            # Normalisierung: Damit es egal ist, wie nah man an der Kamera ist,
            # teilen wir die Lid-Distanz durch die Breite des Gesichts oder Auges.
            # Hier vereinfacht: Wir nehmen die Relation zur Bildhöhe.
            # (Für die Studienarbeit später: "Eye Aspect Ratio" ist die prof. Methode)
            ratio = vertical_distance / h 

            # Zeichne Punkte ins Bild (damit du siehst, was getrackt wird)
            cv2.circle(image, top_point, 3, (0, 255, 0), -1)
            cv2.circle(image, bottom_point, 3, (0, 255, 0), -1)
            cv2.line(image, top_point, bottom_point, (0, 255, 0), 1)

            # --- LOGIK FÜR KLICK ---
            # Anzeige des Wertes auf dem Bildschirm (zum Debuggen)
            cv2.putText(image, f"Ratio: {ratio:.4f}", (30, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

            if ratio < BLINK_THRESHOLD:
                # Auge ist zu!
                if not blink_detected:
                    print("Klick!")
                    mouse.click(Button.left, 1)
                    blink_detected = True
                    # Visuelles Feedback: Text wird Rot
                    cv2.putText(image, "BLINK!", (30, 100), 
                                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            else:
                # Auge ist wieder offen
                blink_detected = False

    cv2.imshow('Eye Tracking Test', image)

    # Abbrechen mit ESC
    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()