import signal
import sys
import time

import numpy as np
import RPi.GPIO as GPIO

from utils.detect import get_target_detection, log_tracking_debug
from utils.servo_config import (
    CREEP_LOOP_SLEEP_SEC,
    CREEP_MAX_STEP_DEG,
    CREEP_MIN_INTERVAL_SEC,
    CREEP_MIN_STEP_DEG,
    PAN_MAX_ANGLE,
    PAN_MIN_ANGLE,
    TRACK_LOST_FRAMES,
    TRACK_LOST_HOLD_SEC,
    X_SERVO_PIN,
    Y_MAX_ANGLE,
    Y_MIN_ANGLE,
    Y_SERVO_ENABLED,
    Y_SERVO_PIN,
)
from utils.servo_driver import create_driver
from utils.utils import creep_step_degrees, y_offset_to_degrees

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

    def patrol(self, reset_home: bool = False):
        if reset_home:
            self.set_x_angle(0)
            self.set_y_angle(0)

        left_to_right = np.linspace(PAN_MIN_ANGLE, PAN_MAX_ANGLE, 30)
        right_to_left = np.linspace(PAN_MAX_ANGLE, PAN_MIN_ANGLE, 30)
        angles = np.concatenate([left_to_right, right_to_left])

        current = self.current_x_angle
        start_idx = int(np.argmin(np.abs(angles - current)))
        sweep_angles = np.concatenate([angles[start_idx:], angles[:start_idx]])

        for angle in sweep_angles:
            time.sleep(0.25)
            self.set_x_angle(angle)
            detection = get_target_detection()
            if detection is not None:
                log_tracking_debug(
                    detection,
                    decision="PATROL_FOUND",
                    pan_angle=self.current_x_angle,
                )
                return detection.x_norm, detection.y_norm
        return None, None

    def hold_last_angle(self):
        print(
            f"[TARGET] Target lost — holding pan at {self.current_x_angle:.1f}° "
            f"for {TRACK_LOST_HOLD_SEC:.1f}s"
        )
        time.sleep(TRACK_LOST_HOLD_SEC)

    def traverse(self):
        angles = [0, 30, 60, 90, 120, 150, 200, 270]
        for angle in angles:
            self.set_x_angle(angle)
            self.set_y_angle(angle)

    def follow_target(self):
        max_attempts = 10000
        frames_without_target = 0
        last_move_time = 0.0
        exit_reason = "max_attempts"

        for i in range(max_attempts):
            time.sleep(CREEP_LOOP_SLEEP_SEC)
            detection = get_target_detection()

            if detection is None:
                log_tracking_debug(
                    None,
                    decision="NO_PERSON",
                    detail=f"follow_iter={i} misses={frames_without_target + 1}",
                )
                frames_without_target += 1
                if frames_without_target >= TRACK_LOST_FRAMES:
                    exit_reason = "lost"
                    break
                continue

            frames_without_target = 0

            if detection.crosshair_inside_box():
                log_tracking_debug(
                    detection,
                    decision="HOLD",
                    pan_angle=self.current_x_angle,
                    detail="crosshair_inside_box",
                )
                continue

            now = time.monotonic()
            elapsed = now - last_move_time
            if elapsed < CREEP_MIN_INTERVAL_SEC:
                wait_left = CREEP_MIN_INTERVAL_SEC - elapsed
                log_tracking_debug(
                    detection,
                    decision="WAIT_INTERVAL",
                    pan_angle=self.current_x_angle,
                    detail=f"{wait_left:.1f}s_until_move",
                )
                continue

            step_x = creep_step_degrees(
                detection.x_norm, CREEP_MAX_STEP_DEG, CREEP_MIN_STEP_DEG
            )
            if abs(step_x) < 0.1:
                log_tracking_debug(
                    detection,
                    decision="NO_STEP",
                    step_deg=step_x,
                    pan_angle=self.current_x_angle,
                )
            else:
                decision = "PAN_RIGHT" if step_x > 0 else "PAN_LEFT"
                log_tracking_debug(
                    detection,
                    decision=decision,
                    step_deg=step_x,
                    pan_angle=self.current_x_angle,
                )
                self.set_x_angle(self.current_x_angle + step_x)
                last_move_time = now

            if self._tilt is not None:
                step_y = creep_step_degrees(
                    detection.y_norm,
                    CREEP_MAX_STEP_DEG,
                    CREEP_MIN_STEP_DEG,
                    y_offset_to_degrees,
                )
                if abs(step_y) >= 0.1:
                    self.set_y_angle(self.current_y_angle + step_y)

        print(f"[TARGET] Follow ended: {exit_reason}")
        return exit_reason
