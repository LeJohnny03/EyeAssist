"""sixdof_overlay.py – 6DoF Achsen (3x Translation + 3x Rotation) mit MediaPipe"""
import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh

# 3D-Modellpunkte (normalisiert, in mm)
MODEL_POINTS = np.array([
    [0.0,    0.0,    0.0  ],   # Nasenspitze     (1)
    [0.0,   -63.6, -12.5 ],   # Kinn            (152)
    [-43.3,  32.7, -26.0 ],   # Linker Augenwinkel (263)
    [43.3,   32.7, -26.0 ],   # Rechter Augenwinkel (33)
    [-28.9, -28.9, -24.1 ],   # Linker Mundwinkel  (287)
    [28.9,  -28.9, -24.1 ],   # Rechter Mundwinkel (57)
], dtype=np.float64)

LANDMARK_IDS = [1, 152, 263, 33, 287, 57]

AXIS_LENGTH = 60  # px

def get_image_points(lm, w, h):
    pts = []
    for idx in LANDMARK_IDS:
        pts.append([lm[idx].x * w, lm[idx].y * h])
    return np.array(pts, dtype=np.float64)

def solve_pose(image_points, w, h):
    focal = w
    cam_matrix = np.array([
        [focal, 0,     w / 2],
        [0,     focal, h / 2],
        [0,     0,     1    ]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))
    success, rvec, tvec = cv2.solvePnP(
        MODEL_POINTS, image_points, cam_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    return success, rvec, tvec, cam_matrix, dist_coeffs

def draw_6dof_axes(frame, rvec, tvec, cam_matrix, dist_coeffs, origin_2d):
    """Zeichnet 6 Achsen: TX/TY/TZ (Translation) + Pitch/Yaw/Roll (Rotation)"""
    # Rotationsachsen am Nasenspitzen-Ursprung
    axes_3d = np.float64([
        [AXIS_LENGTH, 0, 0],   # X → rechts  (rot)
        [0, -AXIS_LENGTH, 0],  # Y → oben    (grün)
        [0, 0, -AXIS_LENGTH],  # Z → vorne   (blau)
    ])
    proj, _ = cv2.projectPoints(axes_3d, rvec, tvec, cam_matrix, dist_coeffs)
    ox, oy = origin_2d

    colors = [(0, 0, 255), (0, 255, 0), (255, 80, 0)]
    labels = ["X (Yaw)", "Y (Pitch)", "Z (Roll)"]
    for i, (color, label) in enumerate(zip(colors, labels)):
        ex, ey = int(proj[i][0][0]), int(proj[i][0][1])
        cv2.arrowedLine(frame, (ox, oy), (ex, ey), color, 2, tipLength=0.2)
        cv2.putText(frame, label, (ex + 4, ey - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1)

    # Translation-Vektoren als Text-HUD oben links
    tx, ty, tz = tvec.flatten()
    rmat, _ = cv2.Rodrigues(rvec)
    # Euler-Winkel aus Rotationsmatrix
    sy = np.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)
    pitch = np.degrees(np.arctan2(-rmat[2, 0],  sy))
    yaw   = np.degrees(np.arctan2( rmat[1, 0], rmat[0, 0]))
    roll  = np.degrees(np.arctan2( rmat[2, 1], rmat[2, 2]))

    hud_lines = [
        (f"TX={tx:+.1f}mm", (0,   0, 255)),
        (f"TY={ty:+.1f}mm", (0, 255,   0)),
        (f"TZ={tz:+.1f}mm", (255, 80,  0)),
        (f"Pitch={pitch:+.1f}deg", (200, 200,   0)),
        (f"Yaw  ={yaw:+.1f}deg",   (0,   200, 200)),
        (f"Roll ={roll:+.1f}deg",  (200,   0, 200)),
    ]
    for i, (text, color) in enumerate(hud_lines):
        cv2.putText(frame, text, (10, 30 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

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
            image_pts = get_image_points(lm, w, h)
            success, rvec, tvec, cam_matrix, dist_coeffs = solve_pose(image_pts, w, h)

            if success:
                nose_px = (int(lm[1].x * w), int(lm[1].y * h))
                cv2.circle(frame, nose_px, 5, (255, 255, 255), -1)
                draw_6dof_axes(frame, rvec, tvec, cam_matrix, dist_coeffs, nose_px)

        cv2.imshow("6DoF Overlay", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
