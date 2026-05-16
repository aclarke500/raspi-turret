#!/usr/bin/env python3
"""
Bench test: person detection via production utils (TFLite + live camera).

Prerequisites (on Pi):
  - ~/tflite_models/detect.tflite
  - ~/tflite_models/coco_labels.txt (copy from repo coco_labels.txt)
  - pip install -r requirements.txt (includes tflite-runtime)
  - USB webcam on /dev/video0 (OpenCV device index 0)

Run from repo root:
  python hardware_tests/ai_test.py

Offsets are normalized from frame center: x,y in roughly [-1, 1].
  (0, 0) = person at center; +x = right; +y = below center (image Y down).
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.camera import get_current_frame
from utils.detect import get_target_direction
from utils.utils import x_offset_to_degrees, y_offset_to_degrees

NUM_SAMPLES = 10
INTERVAL_SEC = 0.2
CAMERA_WAIT_SEC = 3.0
CAMERA_POLL_SEC = 0.1


def _position_hint(x: float, y: float) -> str:
    parts = []
    if abs(x) < 0.05:
        parts.append("horizontally centered")
    elif x > 0:
        parts.append("right of center")
    else:
        parts.append("left of center")
    if abs(y) < 0.05:
        parts.append("vertically centered")
    elif y > 0:
        parts.append("below center")
    else:
        parts.append("above center")
    return ", ".join(parts)


def wait_for_camera() -> bool:
    deadline = time.monotonic() + CAMERA_WAIT_SEC
    while time.monotonic() < deadline:
        if get_current_frame() is not None:
            return True
        time.sleep(CAMERA_POLL_SEC)
    return False


def main():
    print("[INIT] Waiting for camera frame...")
    if not wait_for_camera():
        print("[ERROR] No camera frame within {:.1f}s".format(CAMERA_WAIT_SEC))
        sys.exit(1)
    print("[INIT] Camera ready")

    seen_person = False
    print(f"[RUN] {NUM_SAMPLES} detections ({INTERVAL_SEC}s apart)")

    for i in range(1, NUM_SAMPLES + 1):
        x, y = get_target_direction()
        label = f"{i:02d}"

        if x is None or y is None:
            print(f"[{label}] NO_PERSON")
        else:
            seen_person = True
            hint = _position_hint(x, y)
            deg_x = x_offset_to_degrees(x)
            deg_y = y_offset_to_degrees(y)
            print(
                f"[{label}] PERSON  x={x:+.3f}  y={y:+.3f}  "
                f"({hint})  pan={deg_x:+.1f}°  tilt={deg_y:+.1f}°"
            )

        if i < NUM_SAMPLES:
            time.sleep(INTERVAL_SEC)

    if seen_person:
        print("[DONE] At least one person detected")
        sys.exit(0)
    print("[DONE] No person detected in any sample")
    sys.exit(1)


if __name__ == "__main__":
    main()
