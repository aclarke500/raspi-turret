#!/usr/bin/env python3
"""
Bench test: person detection via production stack (TFLite + live camera).

Prerequisites (on Pi):
  - ~/tflite_models/detect.tflite
  - ~/tflite_models/coco_labels.txt (copy from repo coco_labels.txt)
  - pip install -e . && pip install -r requirements.txt
  - USB webcam on /dev/video0 (OpenCV device index 0)

Run from repo root:
  python hardware_tests/ai_test.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from raspi_turret.hardware.camera import create_camera
from raspi_turret.vision.detector import PersonDetector
from raspi_turret.vision.geometry import x_offset_to_degrees, y_offset_to_degrees

RUN_DURATION_SEC = 5 * 60
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


def wait_for_camera(camera) -> bool:
    deadline = time.monotonic() + CAMERA_WAIT_SEC
    while time.monotonic() < deadline:
        if camera.get_frame() is not None:
            return True
        time.sleep(CAMERA_POLL_SEC)
    return False


def main():
    camera = create_camera()
    detector = PersonDetector()
    camera.start()

    print("[INIT] Waiting for camera frame...")
    try:
        if not wait_for_camera(camera):
            print(f"[ERROR] No camera frame within {CAMERA_WAIT_SEC:.1f}s")
            sys.exit(1)
        print("[INIT] Camera ready")

        seen_person = False
        end_time = time.monotonic() + RUN_DURATION_SEC
        print(
            f"[RUN] Detecting for up to {RUN_DURATION_SEC // 60} min "
            f"({INTERVAL_SEC}s apart); Ctrl+C to stop early"
        )

        i = 0
        try:
            while time.monotonic() < end_time:
                i += 1
                x, y = detector.get_target_direction(camera)
                label = f"{i:04d}"

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

                if time.monotonic() + INTERVAL_SEC < end_time:
                    time.sleep(INTERVAL_SEC)
        except KeyboardInterrupt:
            print("\n[STOP] Interrupted by user")

        if seen_person:
            print(f"[DONE] At least one person detected ({i} samples)")
            sys.exit(0)
        print(f"[DONE] No person detected ({i} samples)")
        sys.exit(1)
    finally:
        camera.stop()


if __name__ == "__main__":
    main()
