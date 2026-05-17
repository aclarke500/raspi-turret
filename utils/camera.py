import cv2
import threading
import time
import atexit
from datetime import datetime

import numpy as np

from utils.camera_config import (
    DEBUG_FRAME_DIFF,
    DIFF_SAMPLE_SIZE,
    MIN_FRAME_DIFF,
    apply_frame_transform,
    format_timestamp,
)

FRAME_SIZE = (1280, 720)
WARMUP_FRAMES = 10
MIN_FRAME_MEAN = 5.0  # skip near-black frames until exposure settles

cap = cv2.VideoCapture(0)
current_frame = None
current_frame_captured_at: str | None = None
frame_lock = threading.Lock()

_last_small_frame: np.ndarray | None = None
_last_stale_log_time = 0.0


def _check_frame_diff(resized: np.ndarray) -> float | None:
    """Downsampled mean absolute diff vs previous frame; None if first frame."""
    global _last_small_frame

    small = cv2.resize(resized, DIFF_SAMPLE_SIZE)
    if _last_small_frame is None:
        _last_small_frame = small.copy()
        return None

    diff = np.abs(
        small.astype(np.int16) - _last_small_frame.astype(np.int16)
    ).mean()
    _last_small_frame = small.copy()
    return float(diff)


def _warmup_camera():
    if not cap.isOpened():
        print("[ERROR] Could not open camera (device index 0)")
        return

    print(f"[INIT] Warming up camera ({WARMUP_FRAMES} frames)...")
    for _ in range(WARMUP_FRAMES):
        ret, _ = cap.read()
        if not ret:
            print("[WARN] Frame capture failed during warmup")
            time.sleep(0.1)


def update_frame():
    global current_frame, current_frame_captured_at, _last_stale_log_time

    while True:
        ret, frame = cap.read()
        if ret:
            resized = apply_frame_transform(cv2.resize(frame, FRAME_SIZE))
            if resized.mean() < MIN_FRAME_MEAN:
                time.sleep(0.05)
                continue

            if DEBUG_FRAME_DIFF:
                diff = _check_frame_diff(resized)
                if diff is not None and diff < MIN_FRAME_DIFF:
                    now = time.monotonic()
                    if now - _last_stale_log_time >= 1.0:
                        _last_stale_log_time = now
                        print(
                            f"[WARN] Frame barely changed, mean diff={diff:.2f} "
                            f"(threshold {MIN_FRAME_DIFF})"
                        )

            captured_at = format_timestamp(datetime.now())
            with frame_lock:
                current_frame = resized.copy()
                current_frame_captured_at = captured_at
        else:
            print("[WARN] Frame capture failed")
            time.sleep(0.1)


def get_current_frame():
    with frame_lock:
        return current_frame.copy() if current_frame is not None else None


def get_current_frame_with_capture_time():
    with frame_lock:
        if current_frame is None:
            return None, None
        return current_frame.copy(), current_frame_captured_at


def release_camera():
    print("[EXIT] Releasing camera")
    cap.release()


atexit.register(release_camera)

_warmup_camera()
threading.Thread(target=update_frame, daemon=True).start()
