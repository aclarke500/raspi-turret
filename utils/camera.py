import cv2
import threading
import time
import atexit

from utils.camera_config import apply_frame_transform

FRAME_SIZE = (1280, 720)
WARMUP_FRAMES = 10
MIN_FRAME_MEAN = 5.0  # skip near-black frames until exposure settles

cap = cv2.VideoCapture(0)
current_frame = None
frame_lock = threading.Lock()


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
    global current_frame
    while True:
        ret, frame = cap.read()
        if ret:
            resized = apply_frame_transform(cv2.resize(frame, FRAME_SIZE))
            if resized.mean() < MIN_FRAME_MEAN:
                time.sleep(0.05)
                continue
            with frame_lock:
                current_frame = resized.copy()
        else:
            print("[WARN] Frame capture failed")
            time.sleep(0.1)


def get_current_frame():
    with frame_lock:
        return current_frame.copy() if current_frame is not None else None


def release_camera():
    print("[EXIT] Releasing camera")
    cap.release()


atexit.register(release_camera)

_warmup_camera()
threading.Thread(target=update_frame, daemon=True).start()
