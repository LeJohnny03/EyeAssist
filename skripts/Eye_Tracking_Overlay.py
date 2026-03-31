"""eye_overlay.py – Augenwinkel, Iris-Mittelpunkt und 2D-Bewegungsachsen"""
import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh

# Landmark-Indizes
LEFT_IRIS          = 468
RIGHT_IRIS         = 473
LEFT_EYE_INNER     = 133
LEFT_EYE_OUTER     = 33
RIGHT_EYE_INNER    = 362
RIGHT_EYE_OUTER    = 263

def draw_2d_axes(frame, center, iris_delta_x, iris_delta_y, scale=40):
    """Zeichnet 2D-Bewegungsachsen (X/Y-Pfeile) über der Iris."""
    cx, cy = center
    # X-Achse (rot)
    cv2.arrowedLine(frame, (cx, cy),
                    (cx + int(iris_delta_x * scale), cy),
                    (0, 0, 255), 2, tipLength=0.3)
    # Y-Achse (grün)
    cv2.arrowedLine(frame, (cx, cy),
                    (cx, cy + int(iris_delta_y * scale)),
                    (0, 255, 0), 2, tipLength=0.3)
    # Labels
    cv2.putText(frame, "X", (cx + scale + 4, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    cv2.putText(frame, "Y", (cx + 4, cy - scale - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

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

            def px(idx):
                return int(lm[idx].x * w), int(lm[idx].y * h)

            # Augenwinkel (Endpunkte)
            for idx, label in [(LEFT_EYE_OUTER,  "L.outer"),
                                (LEFT_EYE_INNER,  "L.inner"),
                                (RIGHT_EYE_INNER, "R.inner"),
                                (RIGHT_EYE_OUTER, "R.outer")]:
                pt = px(idx)
                cv2.circle(frame, pt, 4, (255, 200, 0), -1)
                cv2.putText(frame, label, (pt[0] + 5, pt[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)

            # Verbindungslinie je Auge
            cv2.line(frame, px(LEFT_EYE_OUTER),  px(LEFT_EYE_INNER),  (255, 200, 0), 1)
            cv2.line(frame, px(RIGHT_EYE_OUTER), px(RIGHT_EYE_INNER), (255, 200, 0), 1)

            # Iris-Mittelpunkte
            l_iris = px(LEFT_IRIS)
            r_iris = px(RIGHT_IRIS)
            cv2.circle(frame, l_iris, 5, (0, 255, 255), -1)
            cv2.circle(frame, r_iris, 5, (0, 255, 255), -1)

            # Iris-Delta relativ zu Augenmittelpunkt
            def center_x(inner, outer):
                return (lm[inner].x + lm[outer].x) / 2
            def center_y(inner, outer):
                return (lm[inner].y + lm[outer].y) / 2

            l_cx = center_x(LEFT_EYE_INNER,  LEFT_EYE_OUTER)
            l_cy = center_y(LEFT_EYE_INNER,  LEFT_EYE_OUTER)
            r_cx = center_x(RIGHT_EYE_INNER, RIGHT_EYE_OUTER)
            r_cy = center_y(RIGHT_EYE_INNER, RIGHT_EYE_OUTER)

            delta_x = ((lm[LEFT_IRIS].x  - l_cx) + (lm[RIGHT_IRIS].x - r_cx)) / 2
            delta_y = ((lm[LEFT_IRIS].y  - l_cy) + (lm[RIGHT_IRIS].y - r_cy)) / 2

            # 2D-Achsen über der linken Iris
            draw_2d_axes(frame, l_iris, delta_x, delta_y, scale=45)

            # Delta-Werte als Text
            cv2.putText(frame, f"iris dx={delta_x:.4f}  dy={delta_y:.4f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)

        cv2.imshow("Eye Tracking Overlay", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
