import sys
from pathlib import Path

import cv2

WARMUP_FRAMES = 10
FRAME_SIZE = (1280, 720)
OUTPUT_PATH = Path(__file__).resolve().parent / "test_camera.jpg"


def main():
    cap = cv2.VideoCapture(0)
    try:
        if not cap.isOpened():
            print("[ERROR] Could not open camera (device index 0)")
            sys.exit(1)

        print(f"[INIT] Warming up camera ({WARMUP_FRAMES} frames)...")
        for _ in range(WARMUP_FRAMES):
            ret, _ = cap.read()
            if not ret:
                print("[WARN] Frame capture failed")
                sys.exit(1)

        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame capture failed")
            sys.exit(1)

        resized = cv2.resize(frame, FRAME_SIZE)
        if not cv2.imwrite(str(OUTPUT_PATH), resized):
            print(f"[ERROR] Failed to write {OUTPUT_PATH}")
            sys.exit(1)

        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.stat().st_size == 0:
            print(f"[ERROR] Output file missing or empty: {OUTPUT_PATH}")
            sys.exit(1)

        print(f"[OK] Saved {OUTPUT_PATH} ({FRAME_SIZE[0]}x{FRAME_SIZE[1]})")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
