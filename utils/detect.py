"""Legacy re-exports — prefer raspi_turret.vision.detector."""

from raspi_turret.hardware.camera import UsbCamera, create_camera
from raspi_turret.vision.detector import (
    DetectionResult,
    PersonDetector,
    annotate_frame,
    log_tracking_debug,
)

_shared_camera: UsbCamera | None = None
_shared_detector: PersonDetector | None = None


def _ensure_bench_stack():
    global _shared_camera, _shared_detector
    if _shared_camera is None:
        _shared_camera = create_camera()
        _shared_camera.start()
    if _shared_detector is None:
        _shared_detector = PersonDetector()


def detect_person(frame):
    _ensure_bench_stack()
    return _shared_detector.detect(frame)


def get_target_detection() -> DetectionResult | None:
    _ensure_bench_stack()
    return _shared_detector.detect_latest(_shared_camera)


def get_target_direction():
    _ensure_bench_stack()
    return _shared_detector.get_target_direction(_shared_camera)


def is_in_safezone(x):
    degrees = 135 * abs(x)
    not_valid = degrees <= 20
    if not_valid:
        print("not valid: ", degrees, " degrees.")
    return degrees <= 20
