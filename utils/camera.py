import cv2
import threading

cap = cv2.VideoCapture(0)
current_frame = None

def update_frame():
    global current_frame
    while True:
        ret, frame = cap.read()
        if ret:
            current_frame = frame

# start grabbing in background
t = threading.Thread(target=update_frame, daemon=True)
t.start()

def get_current_frame():
    return current_frame
