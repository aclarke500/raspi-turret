import RPi.GPIO as GPIO
import time
import numpy as np

# --- GPIO Setup ---
SERVO_PIN = 27  # GPIO 27 = Physical pin 13
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz = 20ms period
pwm.start(0)

def set_angle(angle):
    # clamp angle between 0 and 270 just in case
    angle = max(0, min(270, angle))
    duty = (0.05 * angle) + 2.5
    pwm.ChangeDutyCycle(duty)
    print(f"[CALIBRATE] angle={angle:.1f} → duty={duty:.2f}")
    time.sleep(0.05)
    pwm.ChangeDutyCycle(0)

try:
    # move to 0° and wait
    set_angle(0)
    time.sleep(1)

    for _ in range(3):
        for angle in np.linspace(0, 270, num=60):  # sweep up
            set_angle(angle)
        time.sleep(0.3)
        for angle in np.linspace(270, 0, num=60):  # sweep down
            set_angle(angle)
        time.sleep(0.3)

    # back to 0° for taping
    set_angle(0)
    time.sleep(1)
    print("[CALIBRATE] Motor parked at 0°")

finally:
    pwm.stop()
    GPIO.cleanup()
