"""Servo tuning — shared by Turret and hardware tests."""

# Set True to use pigpio (requires: sudo pigpiod). False = RPi.GPIO software PWM.
USE_PIGPIO = False

Y_SERVO_ENABLED = True

X_SERVO_PIN = 17
Y_SERVO_PIN = 27
PWM_FREQ_HZ = 50

PAN_MIN_ANGLE = 0.0
PAN_MAX_ANGLE = 270.0
# Tilt safe travel: 100° = level/dead-on; do not exceed (turret mechanical limits)
Y_MIN_ANGLE = 75.0
Y_MAX_ANGLE = 125.0
Y_HOME_ANGLE = 100.0


def clamp_y_angle(angle: float) -> float:
    return max(Y_MIN_ANGLE, min(Y_MAX_ANGLE, float(angle)))

SERVO_SETTLE_SEC = 0.25
RELEASE_PULSE_AFTER_MOVE = True
MIN_MOVE_DEG = 2.0
MAX_MOVE_DEG = 8.0
MIN_MOVE_INTERVAL_SEC = 0.15

# Box-center dead zone: crosshair within this fraction of box width/height of centroid
BOX_CENTER_TOLERANCE = 0.05

# Creep tracking: small discrete steps when crosshair is outside center dead zone
CREEP_MIN_INTERVAL_SEC = 1.0
CREEP_MAX_STEP_DEG = 3.0
CREEP_MIN_STEP_DEG = 2.0
CREEP_LOOP_SLEEP_SEC = 0.2

# Follow mode: consecutive frames without person before lost; pause before re-patrol
TRACK_LOST_FRAMES = 6
TRACK_LOST_HOLD_SEC = 2.0

# Web D-pad manual control step size
MANUAL_NUDGE_DEG = 10.0

# pigpio pulse range for 0–270° (matches s.py bench script)
PIGPIO_PULSE_MIN_US = 500
PIGPIO_PULSE_MAX_US = 2500
