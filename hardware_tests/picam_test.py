#!/usr/bin/env python3
"""
Bench test: Raspberry Pi CSI camera via picamera2 (libcamera).

Pi only. Prerequisites:
  - CSI camera connected and enabled (raspi-config / device tree)
  - sudo apt install -y python3-picamera2
  - pip install -r requirements.txt (opencv for imwrite)

Run from repo root:
  python hardware_tests/picam_test.py

Saves one 1280×720 JPEG to hardware_tests/picam_photos/picam_test.jpg
"""
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.camera_config import apply_frame_transform

FRAME_SIZE = (1280, 720)
WARMUP_FRAMES = 10
OUTPUT_DIR = Path(__file__).resolve().parent / "picam_photos"
OUTPUT_FILE = OUTPUT_DIR / "picam_test.jpg"


def is_pi_camera_available(Picamera2):
    info = Picamera2.global_camera_info()
    if not info:
        return None
    for cam in info:
        print(
            f"[INIT] libcamera device id={cam.get('Num', '?')} "
            f"model={cam.get('Model', '?')}"
        )
    return info


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from picamera2 import Picamera2
    except ImportError:
        print(
            "[ERROR] picamera2 not installed. On the Pi run:\n"
            "  sudo apt install -y python3-picamera2"
        )
        sys.exit(1)

    info = is_pi_camera_available(Picamera2)
    if not info:
        print(
            "[ERROR] No libcamera cameras found. Enable the CSI camera in "
            "raspi-config and check the ribbon cable."
        )
        sys.exit(1)

    picam2 = None
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(
            main={"size": FRAME_SIZE, "format": "RGB888"}
        )
        picam2.configure(config)
        picam2.start()

        print(f"[INIT] Warming up Pi camera ({WARMUP_FRAMES} frames)...")
        for i in range(WARMUP_FRAMES):
            picam2.capture_array()
            if i == 0:
                time.sleep(0.2)

        print("[CAPTURE] Taking photo...")
        rgb = picam2.capture_array()
        if rgb is None or rgb.size == 0:
            print("[ERROR] capture_array returned empty frame")
            sys.exit(1)

        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        frame = apply_frame_transform(cv2.resize(bgr, FRAME_SIZE))

        if not cv2.imwrite(str(OUTPUT_FILE), frame):
            print(f"[ERROR] Failed to write {OUTPUT_FILE}")
            sys.exit(1)

        if not OUTPUT_FILE.is_file() or OUTPUT_FILE.stat().st_size == 0:
            print(f"[ERROR] Output file missing or empty: {OUTPUT_FILE}")
            sys.exit(1)

        print(f"[OK] Saved {OUTPUT_FILE}")
        print(
            f"[DONE] Pi camera test passed ({FRAME_SIZE[0]}x{FRAME_SIZE[1]}) "
            f"— {len(info)} libcamera device(s) seen"
        )
    except Exception as e:
        print(f"[ERROR] Pi camera capture failed: {e}")
        sys.exit(1)
    finally:
        if picam2 is not None:
            try:
                picam2.stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
