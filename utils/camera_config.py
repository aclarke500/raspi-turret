"""Camera orientation — shared by utils/camera.py and hardware_tests/camera_test.py."""

import cv2

# Set True if the webcam is mounted upside down (180° rotation).
FLIP_UPSIDE_DOWN = True


def apply_frame_transform(frame):
    if FLIP_UPSIDE_DOWN:
        return cv2.flip(frame, -1)
    return frame
