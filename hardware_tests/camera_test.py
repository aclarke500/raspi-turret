import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.camera_config import apply_frame_transform

WARMUP_FRAMES = 10
NUM_PHOTOS = 10
INTERVAL_SEC = 0.1
FRAME_SIZE = (1280, 720)
OUTPUT_DIR = Path(__file__).resolve().parent / "test_photos"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

        print(f"[CAPTURE] Taking {NUM_PHOTOS} photos ({INTERVAL_SEC}s apart)...")
        saved = []
        for i in range(1, NUM_PHOTOS + 1):
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Frame capture failed")
                sys.exit(1)

            resized = apply_frame_transform(cv2.resize(frame, FRAME_SIZE))
            out_path = OUTPUT_DIR / f"frame_{i:02d}.jpg"
            if not cv2.imwrite(str(out_path), resized):
                print(f"[ERROR] Failed to write {out_path}")
                sys.exit(1)

            if not out_path.is_file() or out_path.stat().st_size == 0:
                print(f"[ERROR] Output file missing or empty: {out_path}")
                sys.exit(1)

            saved.append(out_path)
            print(f"[OK] Saved {out_path}")

            if i < NUM_PHOTOS:
                time.sleep(INTERVAL_SEC)

        print(f"[DONE] {len(saved)} photos in {OUTPUT_DIR} ({FRAME_SIZE[0]}x{FRAME_SIZE[1]})")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
