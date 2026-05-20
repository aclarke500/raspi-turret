"""Camera orientation and debug — shared by utils/camera.py and hardware_tests/camera_test.py."""

from datetime import datetime

import cv2

# Set True if the webcam is mounted upside down (180° rotation).
FLIP_UPSIDE_DOWN = False

# Log when consecutive captures are nearly identical (stuck / duplicate frames).
DEBUG_FRAME_DIFF = True
MIN_FRAME_DIFF = 1.0
DIFF_SAMPLE_SIZE = (160, 90)


def format_timestamp(dt=None) -> str:
    """Wall-clock time as HH:MM:SS:mmm (milliseconds)."""
    dt = dt or datetime.now()
    return dt.strftime("%H:%M:%S:") + f"{dt.microsecond // 1000:03d}"


def apply_frame_transform(frame):
    if FLIP_UPSIDE_DOWN:
        return cv2.flip(frame, -1)
    return frame
