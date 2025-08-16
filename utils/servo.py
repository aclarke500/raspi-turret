import RPi.GPIO as GPIO
import numpy as np
import tflite_runtime.interpreter as tflite
import time
# Pin config
SERVO_PIN = 17  # GPIO 17 = Physical pin 11

print("[INIT] Setting up GPIO mode...")
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

print("[INIT] Starting PWM on pin 17 at 50Hz (20ms period)...")
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for servo control
pwm.start(0)  # initial duty cycle





def set_angle(angle):
    # Convert angle (0–180) to duty cycle
    duty = (0.05 * angle) + 2.5
    print(f"[MOVE] Setting angle to {angle}°, which maps to duty cycle {duty:.2f}%")
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)

def cleanup():
    set_angle(0)
    pwm.stop()