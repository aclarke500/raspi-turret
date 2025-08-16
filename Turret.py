import time
import RPi.GPIO as GPIO
import tflite_runtime.interpreter as tflite
import numpy as np
import signal
import sys

SERVO_PIN = 17  # GPIO 17 = Physical pin 11

def cleanup_and_exit(signum, frame):
    print("\n[SHUTDOWN] Cleaning up GPIO...")
    pwm.stop()
    GPIO.cleanup()
    print("[SHUTDOWN] GPIO cleanup complete")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, cleanup_and_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_and_exit)  # Termination signal

print("[INIT] Setting up GPIO mode...")
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

print("[INIT] Starting PWM on pin 17 at 50Hz (20ms period)...")
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for servo control
pwm.start(0)  # initial duty cycle

class Turret:
    def __init__(self):
        self.current_x_angle = 0
        self.SERVO_PIN = SERVO_PIN
        self.target_location = None

    def setup(self):
        self.set_angle(0)


    def set_angle(self, angle):
         # Convert angle (0–180) to duty cycle
        duty = (0.05 * angle) + 2.5
        print(f"[MOVE] Setting angle to {angle}°, which maps to duty cycle {duty:.2f}%")
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.1)

    def patrol(self):
        self.set_angle(0)
        left_to_right = np.linspace(0, 270, 30)
        right_to_left  = np.linspace(270, 0, 30)
        angles = np.concatenate([left_to_right, right_to_left])
        for angle in angles:
            self.set_angle(angle)

