"""Servo tuning — shared by Turret and hardware tests."""

# Set True to use pigpio (requires: sudo pigpiod). False = RPi.GPIO software PWM.
USE_PIGPIO = False

# Tilt servo disabled in production until set_y_angle early-return is removed.
Y_SERVO_ENABLED = False

X_SERVO_PIN = 17
Y_SERVO_PIN = 27
PWM_FREQ_HZ = 50

PAN_MIN_ANGLE = 0.0
PAN_MAX_ANGLE = 270.0
Y_MIN_ANGLE = 0.0
Y_MAX_ANGLE = 135.0

SERVO_SETTLE_SEC = 0.25
RELEASE_PULSE_AFTER_MOVE = True
MIN_MOVE_DEG = 2.0
MAX_MOVE_DEG = 8.0
MIN_MOVE_INTERVAL_SEC = 0.15

# Tracking: normalized offset from frame center below this → considered centered
CENTER_DEADBAND = 0.05

# Creep tracking: small discrete steps when target is outside deadband
CREEP_MIN_INTERVAL_SEC = 1.0
CREEP_MAX_STEP_DEG = 3.0
CREEP_MIN_STEP_DEG = 2.0
CREEP_LOOP_SLEEP_SEC = 0.2

# pigpio pulse range for 0–270° (matches s.py bench script)
PIGPIO_PULSE_MIN_US = 500
PIGPIO_PULSE_MAX_US = 2500
