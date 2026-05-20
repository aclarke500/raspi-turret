import threading
import time

import numpy as np

from raspi_turret.config.servo import (
    CREEP_LOOP_SLEEP_SEC,
    CREEP_MAX_STEP_DEG,
    CREEP_MIN_INTERVAL_SEC,
    CREEP_MIN_STEP_DEG,
    MANUAL_NUDGE_DEG,
    PAN_MAX_ANGLE,
    PAN_MIN_ANGLE,
    TRACK_LOST_FRAMES,
    TRACK_LOST_HOLD_SEC,
    Y_HOME_ANGLE,
    Y_MAX_ANGLE,
    Y_MIN_ANGLE,
    clamp_y_angle,
)
from raspi_turret.hardware.camera import Camera
from raspi_turret.hardware.servo import ServoMotor
from raspi_turret.vision.detector import PersonDetector, log_tracking_debug
from raspi_turret.vision.geometry import creep_step_degrees, y_offset_to_degrees


class Turret:
    def __init__(
        self,
        pan: ServoMotor,
        detector: PersonDetector,
        camera: Camera,
        tilt: ServoMotor | None = None,
    ):
        self._pan = pan
        self._tilt = tilt
        self._detector = detector
        self._camera = camera
        self.target_location = None
        self._servo_lock = threading.RLock()

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
        self.rotate_y_servo(Y_HOME_ANGLE)

    def cleanup(self):
        self._pan.stop()
        if self._tilt is not None:
            self._tilt.stop()
        print("[SHUTDOWN] Turret servos stopped.")

    def set_x_angle(self, angle):
        with self._servo_lock:
            return self._pan.set_angle(angle)

    def rotate_y_servo(self, angle: float) -> bool:
        if self._tilt is None:
            return False
        requested = float(angle)
        safe_angle = clamp_y_angle(requested)
        if safe_angle != requested:
            print(
                f"[WARN] Y angle clamped {requested:.1f}° → {safe_angle:.1f}° "
                f"(safe range {Y_MIN_ANGLE:.0f}–{Y_MAX_ANGLE:.0f}°, home={Y_HOME_ANGLE:.0f}°)"
            )
        with self._servo_lock:
            return self._tilt.set_angle(safe_angle)

    def set_y_angle(self, angle):
        return self.rotate_y_servo(angle)

    def nudge(self, direction: str) -> dict:
        direction = direction.lower().strip()
        valid = frozenset({"left", "right", "up", "down"})
        if direction not in valid:
            raise ValueError(
                f"Invalid direction {direction!r}; use left, right, up, or down"
            )

        with self._servo_lock:
            pan_moved = False
            tilt_moved = False
            step = MANUAL_NUDGE_DEG

            if direction == "left":
                pan_moved = self._pan.set_angle(self.current_x_angle - step)
            elif direction == "right":
                pan_moved = self._pan.set_angle(self.current_x_angle + step)
            elif direction in ("up", "down"):
                if self._tilt is None:
                    raise RuntimeError("Tilt servo not enabled")
                if direction == "up":
                    tilt_moved = self._tilt.set_angle(
                        clamp_y_angle(self.current_y_angle - step)
                    )
                else:
                    tilt_moved = self._tilt.set_angle(
                        clamp_y_angle(self.current_y_angle + step)
                    )

        print(
            f"[MANUAL] nudge {direction} → pan={self.current_x_angle:.1f}° "
            f"tilt={self.current_y_angle:.1f}°"
        )
        return {
            "ok": True,
            "direction": direction,
            "x_angle": self.current_x_angle,
            "y_angle": self.current_y_angle,
            "pan_moved": pan_moved,
            "tilt_moved": tilt_moved,
        }

    def _get_detection(self):
        return self._detector.detect_latest(self._camera)

    def patrol(self, reset_home: bool = False):
        if reset_home:
            self.set_x_angle(0)
            self.rotate_y_servo(Y_HOME_ANGLE)

        left_to_right = np.linspace(PAN_MIN_ANGLE, PAN_MAX_ANGLE, 30)
        right_to_left = np.linspace(PAN_MAX_ANGLE, PAN_MIN_ANGLE, 30)
        angles = np.concatenate([left_to_right, right_to_left])

        current = self.current_x_angle
        start_idx = int(np.argmin(np.abs(angles - current)))
        sweep_angles = np.concatenate([angles[start_idx:], angles[:start_idx]])

        for angle in sweep_angles:
            time.sleep(0.25)
            self.set_x_angle(angle)
            detection = self._get_detection()
            if detection is not None:
                log_tracking_debug(
                    detection,
                    decision="PATROL_FOUND",
                    pan_angle=self.current_x_angle,
                )
                return detection.x_norm, detection.y_norm
        return None, None

    def hold_last_angle(self):
        if self._tilt is not None:
            print(
                f"[TARGET] Target lost — holding pan {self.current_x_angle:.1f}° "
                f"tilt {self.current_y_angle:.1f}° for {TRACK_LOST_HOLD_SEC:.1f}s"
            )
        else:
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
            detection = self._get_detection()

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

            if detection.is_centered_on_box():
                log_tracking_debug(
                    detection,
                    decision="HOLD",
                    pan_angle=self.current_x_angle,
                    tilt_angle=self.current_y_angle,
                    detail="within_box_center_deadzone",
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
                    tilt_angle=self.current_y_angle,
                    detail=f"{wait_left:.1f}s_until_move",
                )
                continue

            step_x = creep_step_degrees(
                detection.x_norm, CREEP_MAX_STEP_DEG, CREEP_MIN_STEP_DEG
            )
            step_y = 0.0
            if self._tilt is not None:
                step_y = creep_step_degrees(
                    detection.y_norm,
                    CREEP_MAX_STEP_DEG,
                    CREEP_MIN_STEP_DEG,
                    y_offset_to_degrees,
                )

            move_parts = []
            if abs(step_x) >= 0.1:
                move_parts.append("PAN_RIGHT" if step_x > 0 else "PAN_LEFT")
                self.set_x_angle(self.current_x_angle + step_x)
            if self._tilt is not None and abs(step_y) >= 0.1:
                move_parts.append("TILT_UP" if step_y > 0 else "TILT_DOWN")
                self.rotate_y_servo(self.current_y_angle + step_y)

            if move_parts:
                log_tracking_debug(
                    detection,
                    decision="+".join(move_parts),
                    step_deg=step_x if abs(step_x) >= 0.1 else None,
                    step_y_deg=step_y if abs(step_y) >= 0.1 else None,
                    pan_angle=self.current_x_angle,
                    tilt_angle=self.current_y_angle,
                )
                last_move_time = now
            else:
                log_tracking_debug(
                    detection,
                    decision="NO_STEP",
                    step_deg=step_x,
                    step_y_deg=step_y,
                    pan_angle=self.current_x_angle,
                    tilt_angle=self.current_y_angle,
                )

        print(f"[TARGET] Follow ended: {exit_reason}")
        return exit_reason
