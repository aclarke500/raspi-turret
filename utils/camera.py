import cv2
import threading
import time
import atexit

cap = cv2.VideoCapture(0)
current_frame = None
frame_lock = threading.Lock()

def update_frame():
    global current_frame
    while True:
        ret, frame = cap.read()
        if ret:
            resized = cv2.resize(frame, (1280, 720))  # resize if needed
            with frame_lock:
                current_frame = resized.copy()
        else:
            print("[WARN] Frame capture failed")
            time.sleep(0.1)  # avoid tight loop on failure

def get_current_frame():
    with frame_lock:
        return current_frame.copy() if current_frame is not None else None

def release_camera():
    print("[EXIT] Releasing camera")
    cap.release()

# cleanup on exit
atexit.register(release_camera)

# start grabbing in background
threading.Thread(target=update_frame, daemon=True).start()
