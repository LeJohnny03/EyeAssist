"""head_overlay.py – Nasenspitze als Referenz + 2D-Bewegungsachsen"""
import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

NOSE_TIP = 1

# Kalibrierungs-Referenz (wird beim ersten stabilen Frame gesetzt)
ref_x, ref_y = None, None
CALIB_FRAMES  = 30
calib_counter = 0
calib_sum     = [0.0, 0.0]

def draw_2d_axes(frame, center, delta_x, delta_y, scale=60):
    cx, cy = center
    end_x = cx + int(delta_x * scale)
    end_y = cy + int(delta_y * scale)
    # X-Achse (rot)
    cv2.arrowedLine(frame, (cx, cy), (end_x, cy),
                    (0, 0, 255), 2, tipLength=0.25)
    # Y-Achse (grün)
    cv2.arrowedLine(frame, (cx, cy), (cx, end_y),
                    (0, 255, 0), 2, tipLength=0.25)
    # Diagonale Bewegungsrichtung (blau)
    cv2.arrowedLine(frame, (cx, cy), (end_x, end_y),
                    (255, 100, 0), 2, tipLength=0.2)
    # Referenz-Kreis
    cv2.circle(frame, center, 6, (255, 255, 255), 2)
    cv2.circle(frame, center, scale, (80, 80, 80), 1)
    cv2.putText(frame, "X", (cx + scale + 5, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    cv2.putText(frame, "Y", (cx + 5, cy - scale - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

cap = cv2.VideoCapture(0)

with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as face_mesh:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            nose = lm[NOSE_TIP]
            nx, ny = int(nose.x * w), int(nose.y * h)

            # Auto-Kalibrierung über erste N Frames
            if calib_counter < CALIB_FRAMES:
                calib_sum[0] += nose.x
                calib_sum[1] += nose.y
                calib_counter += 1
                ref_x = calib_sum[0] / calib_counter
                ref_y = calib_sum[1] / calib_counter
                cv2.putText(frame, f"Kalibrierung... {calib_counter}/{CALIB_FRAMES}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            else:
                delta_x = nose.x - ref_x
                delta_y = nose.y - ref_y

                # Nasenspitze
                cv2.circle(frame, (nx, ny), 6, (0, 140, 255), -1)
                cv2.putText(frame, "Nase", (nx + 8, ny - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 140, 255), 1)

                # 2D-Achsen
                draw_2d_axes(frame, (nx, ny), delta_x, delta_y, scale=80)

                # Referenzkreuz
                ref_px = int(ref_x * w)
                ref_py = int(ref_y * h)
                cv2.drawMarker(frame, (ref_px, ref_py), (200, 200, 200),
                               cv2.MARKER_CROSS, 14, 1)
                cv2.putText(frame, "Ref", (ref_px + 8, ref_py - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

                cv2.putText(frame,
                            f"head dx={delta_x:.4f}  dy={delta_y:.4f}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (0, 140, 255), 1)

        cv2.imshow("Head Tracking Overlay", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
