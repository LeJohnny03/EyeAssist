import cv2


def open_camera(index: int):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return None
    return cap
