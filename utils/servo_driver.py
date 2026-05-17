"""Pan/tilt servo drivers: RPi.GPIO with release-pulse, optional pigpio."""

import time

import RPi.GPIO as GPIO

from utils.servo_config import (
    MIN_MOVE_DEG,
    MIN_MOVE_INTERVAL_SEC,
    PIGPIO_PULSE_MAX_US,
    PIGPIO_PULSE_MIN_US,
    PWM_FREQ_HZ,
    RELEASE_PULSE_AFTER_MOVE,
    SERVO_SETTLE_SEC,
    USE_PIGPIO,
)


def angle_to_duty(angle: float) -> float:
    return (0.05 * angle) + 2.5


def angle_to_pulse_us(angle: float, min_angle: float, max_angle: float) -> int:
    angle = max(min_angle, min(max_angle, angle))
    span = max_angle - min_angle
    if span <= 0:
        return PIGPIO_PULSE_MIN_US
    t = (angle - min_angle) / span
    return int(PIGPIO_PULSE_MIN_US + t * (PIGPIO_PULSE_MAX_US - PIGPIO_PULSE_MIN_US))


class GpioPwmDriver:
    def __init__(self, pin: int, min_angle: float, max_angle: float):
        self._pin = pin
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._current_angle = min_angle
        self._last_move_time = 0.0
        self._pwm = None

    @property
    def current_angle(self) -> float:
        return self._current_angle

    def start(self):
        GPIO.setup(self._pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self._pin, PWM_FREQ_HZ)
        self._pwm.start(0)

    def set_angle(self, angle: float) -> bool:
        angle = max(self._min_angle, min(self._max_angle, float(angle)))
        if abs(angle - self._current_angle) < MIN_MOVE_DEG:
            return False
        now = time.monotonic()
        if now - self._last_move_time < MIN_MOVE_INTERVAL_SEC:
            return False

        duty = angle_to_duty(angle)
        self._pwm.ChangeDutyCycle(duty)
        time.sleep(SERVO_SETTLE_SEC)
        if RELEASE_PULSE_AFTER_MOVE:
            self._pwm.ChangeDutyCycle(0)

        self._current_angle = angle
        self._last_move_time = now
        return True

    def stop(self):
        if self._pwm is not None:
            self._pwm.stop()
            self._pwm = None


class PigpioDriver:
    def __init__(self, pin: int, min_angle: float, max_angle: float):
        import pigpio

        self._pin = pin
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._current_angle = min_angle
        self._last_move_time = 0.0
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError("pigpio not connected — run: sudo pigpiod")

    @property
    def current_angle(self) -> float:
        return self._current_angle

    def start(self):
        self._pi.set_servo_pulsewidth(self._pin, 0)

    def set_angle(self, angle: float) -> bool:
        angle = max(self._min_angle, min(self._max_angle, float(angle)))
        if abs(angle - self._current_angle) < MIN_MOVE_DEG:
            return False
        now = time.monotonic()
        if now - self._last_move_time < MIN_MOVE_INTERVAL_SEC:
            return False

        pulse = angle_to_pulse_us(angle, self._min_angle, self._max_angle)
        self._pi.set_servo_pulsewidth(self._pin, pulse)
        time.sleep(SERVO_SETTLE_SEC)
        if RELEASE_PULSE_AFTER_MOVE:
            self._pi.set_servo_pulsewidth(self._pin, 0)

        self._current_angle = angle
        self._last_move_time = now
        return True

    def stop(self):
        self._pi.set_servo_pulsewidth(self._pin, 0)
        self._pi.stop()


def create_driver(pin: int, min_angle: float, max_angle: float):
    if USE_PIGPIO:
        return PigpioDriver(pin, min_angle, max_angle)
    return GpioPwmDriver(pin, min_angle, max_angle)
