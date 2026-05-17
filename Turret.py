import signal
import sys
import time

import numpy as np
import RPi.GPIO as GPIO

from utils.detect import get_target_direction
from utils.servo_config import (
    CENTER_DEADBAND,
    MAX_MOVE_DEG,
    PAN_MAX_ANGLE,
    PAN_MIN_ANGLE,
    X_SERVO_PIN,
    Y_MAX_ANGLE,
    Y_MIN_ANGLE,
    Y_SERVO_ENABLED,
    Y_SERVO_PIN,
)
from utils.servo_driver import create_driver
from utils.utils import x_offset_to_degrees, y_offset_to_degrees

_pan_driver = None
_tilt_driver = None
_gpio_mode_set = False


def _ensure_gpio_mode():
    global _gpio_mode_set
    if not _gpio_mode_set:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        _gpio_mode_set = True


def _get_pan_driver():
    global _pan_driver
    _ensure_gpio_mode()
    if _pan_driver is None:
        print("[INIT] Starting pan servo driver...")
        _pan_driver = create_driver(X_SERVO_PIN, PAN_MIN_ANGLE, PAN_MAX_ANGLE)
        _pan_driver.start()
    return _pan_driver


def _get_tilt_driver():
    global _tilt_driver
    if not Y_SERVO_ENABLED:
        return None
    _ensure_gpio_mode()
    if _tilt_driver is None:
        print("[INIT] Starting tilt servo driver...")
        _tilt_driver = create_driver(Y_SERVO_PIN, Y_MIN_ANGLE, Y_MAX_ANGLE)
        _tilt_driver.start()
    return _tilt_driver


def _stop_drivers():
    global _pan_driver, _tilt_driver
    if _pan_driver is not None:
        _pan_driver.stop()
        _pan_driver = None
    if _tilt_driver is not None:
        _tilt_driver.stop()
        _tilt_driver = None
    if _gpio_mode_set:
        GPIO.cleanup()
        _gpio_mode_set = False


def cleanup_and_exit(signum, frame):
    print("\n[SHUTDOWN] Cleaning up GPIO...")
    _stop_drivers()
    print("[SHUTDOWN] GPIO cleanup complete")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)


class Turret:
    def __init__(self):
        self._pan = _get_pan_driver()
        self._tilt = _get_tilt_driver()
        self.target_location = None

    @property
    def current_x_angle(self) -> float:
        return self._pan.current_angle

    @property
    def current_y_angle(self) -> float:
        if self._tilt is None:
            return 0.0
        return self._tilt.current_angle

    def setup(self):
        self.set_x_angle(0)
        self.set_y_angle(0)

    def cleanup(self):
        _stop_drivers()
        print("[SHUTDOWN] Cleanup done.")

    def set_x_angle(self, angle):
        moved = self._pan.set_angle(angle)
        return moved

    def set_y_angle(self, angle):
        if self._tilt is None:
            return False
        return self._tilt.set_angle(angle)

    def patrol(self):
        self.set_x_angle(0)
        self.set_y_angle(0)
        left_to_right = np.linspace(PAN_MIN_ANGLE, PAN_MAX_ANGLE, 30)
        right_to_left = np.linspace(PAN_MAX_ANGLE, PAN_MIN_ANGLE, 30)
        angles = np.concatenate([left_to_right, right_to_left])
        for angle in angles:
            time.sleep(0.25)
            self.set_x_angle(angle)
            x_offset_of_target, y_offset_of_target = get_target_direction()
            if x_offset_of_target is not None:
                degrees_offset = x_offset_to_degrees(x_offset_of_target)
                target_angle = self.current_x_angle + degrees_offset
                print(
                    f"[TARGET] Found target! X offset: {x_offset_of_target:.2f}, "
                    f"Degrees offset: {degrees_offset:.1f}°, Current angle: {self.current_x_angle:.1f}°, "
                    f"Target angle: {target_angle:.1f}°"
                )
                return x_offset_of_target, y_offset_of_target
        return None, None

    def traverse(self):
        angles = [0, 30, 60, 90, 120, 150, 200, 270]
        for angle in angles:
            self.set_x_angle(angle)
            self.set_y_angle(angle)

    def snap_to_target(self, x_offset_degrees, y_offset_degrees):
        max_attempts = 100
        frames_without_target = 0
        x_offset_of_target = None
        y_offset_of_target = None

        for i in range(max_attempts):
            time.sleep(0.3)
            x_offset_of_target, y_offset_of_target = get_target_direction()

            if x_offset_of_target is None:
                print(f"[TARGET] No target (snap {i})")
                frames_without_target += 1
                if frames_without_target > 5:
                    break
                continue

            frames_without_target = 0

            if abs(x_offset_of_target) < CENTER_DEADBAND:
                print(
                    f"[TARGET] Target acquired! X offset: {x_offset_of_target:.2f}, "
                    f"angle: {self.current_x_angle:.1f}°"
                )
                break

            step_x = x_offset_to_degrees(x_offset_of_target)
            step_x = max(-MAX_MOVE_DEG, min(MAX_MOVE_DEG, step_x))
            if abs(step_x) >= 0.1:
                print(f"[TARGET] Snap {i}: step {step_x:+.1f}° (x_norm={x_offset_of_target:+.2f})")
                self.set_x_angle(self.current_x_angle + step_x)

            if self._tilt is not None and y_offset_of_target is not None:
                step_y = y_offset_to_degrees(y_offset_of_target)
                step_y = max(-MAX_MOVE_DEG, min(MAX_MOVE_DEG, step_y))
                if abs(step_y) >= 0.1:
                    self.set_y_angle(self.current_y_angle + step_y)

        return x_offset_of_target, y_offset_of_target
