"""Legacy helpers — no import-time capture thread. Prefer raspi_turret.hardware.camera."""

from raspi_turret.hardware.camera import UsbCamera, create_camera

_shared_camera: UsbCamera | None = None


def _shared() -> UsbCamera:
    global _shared_camera
    if _shared_camera is None:
        _shared_camera = create_camera()
        _shared_camera.start()
    return _shared_camera


def get_current_frame():
    return _shared().get_frame()


def get_current_frame_with_capture_time():
    return _shared().get_frame_with_capture_time()


def release_camera():
    global _shared_camera
    if _shared_camera is not None:
        _shared_camera.stop()
        _shared_camera = None
