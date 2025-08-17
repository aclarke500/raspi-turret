import time
import RPi.GPIO as GPIO
import tflite_runtime.interpreter as tflite
import numpy as np
import signal
import sys
from utils.detect import get_target_direction
from utils.utils import x_offset_to_degrees

X_SERVO_PIN = 17  # GPIO 17 = Physical pin 11
Y_SERVO_PIN = 27  # GPIO 27 = Physical pin 13

def cleanup_and_exit(signum, frame):
    print("\n[SHUTDOWN] Cleaning up GPIO...")
    pwm_x.stop()
    pwm_y.stop()  # Add this line
    GPIO.cleanup()
    print("[SHUTDOWN] GPIO cleanup complete")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, cleanup_and_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_and_exit)  # Termination signal

print("[INIT] Setting up GPIO mode...")
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Suppress GPIO warnings
GPIO.setup(X_SERVO_PIN, GPIO.OUT)
GPIO.setup(Y_SERVO_PIN, GPIO.OUT)

print("[INIT] Starting PWM on pin 17 at 50Hz (20ms period)...")
pwm_x = GPIO.PWM(X_SERVO_PIN, 50)  # 50Hz for servo control
pwm_x.start(0)  # initial duty cycle
pwm_y = GPIO.PWM(Y_SERVO_PIN, 50)  # 50Hz for servo control
pwm_y.start(0)  # initial duty cycle

class Turret:
    def __init__(self):
        self.current_x_angle = 0
        self.current_y_angle = 0
        self.X_SERVO_PIN = X_SERVO_PIN
        self.target_location = None

    def setup(self):
        self.set_x_angle(0)
        self.set_y_angle(0)

    def cleanup(self):
        pwm_x.stop()
        pwm_y.stop()
        GPIO.cleanup()
        print("[SHUTDOWN] Cleanup done.")


    def set_x_angle(self, angle):
         # Convert angle (0–180) to duty cycle
        angle = max(0, min(270, angle))
        duty = (0.05 * angle) + 2.5
        # print(f"[MOVE] Setting x angle to {angle}°, which maps to duty cycle {duty:.2f}%")
        pwm_x.ChangeDutyCycle(duty)
        self.current_x_angle = angle
        time.sleep(0.1)

    def set_y_angle(self, angle):
        return # we have disabled y servo for now
        angle = max(0, min(135, angle))
        duty = (0.05 * angle) + 2.5
        print(f"[MOVE] Setting y angle to {angle}°, which maps to duty cycle {duty:.2f}%")
        pwm_y.ChangeDutyCycle(duty)
        self.current_y_angle = angle
        time.sleep(0.1)

    def patrol(self):
        self.set_x_angle(0)
        self.set_y_angle(0)
        left_to_right = np.linspace(0, 270, 30)
        right_to_left  = np.linspace(270, 0, 30)
        angles = np.concatenate([left_to_right, right_to_left])
        for angle in angles:
            self.set_x_angle(angle)
            # returns offset [-1, 1] or None if no one is seen
            x_offset_of_target, y_offset_of_target = get_target_direction()
            if not x_offset_of_target is None:
                degrees_offset = x_offset_to_degrees(x_offset_of_target)
                target_angle = self.current_x_angle + degrees_offset
                print(f"[TARGET] Found target! X offset: {x_offset_of_target:.2f}, " 
                      f"Degrees offset: {degrees_offset:.1f}°, Current angle: {self.current_x_angle:.1f}°, "
                      f"Target angle: {target_angle:.1f}°")
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
        for i in range(max_attempts):
            print("Snapping to target iteration", i)
            self.set_x_angle(self.current_x_angle + x_offset_degrees)
            self.set_y_angle(self.current_y_angle + y_offset_degrees)
            time.sleep(0.1)  # give model time to see new position
            x_offset_of_target, y_offset_of_target = get_target_direction()
            if x_offset_of_target is None:
                print("No target found")
                frames_without_target += 1
                if frames_without_target > 10:
                    break
                time.sleep(0.5)
                continue
            print("Target found")
            frames_without_target = 0
            offset_degrees = x_offset_to_degrees(x_offset_of_target)
            if abs(offset_degrees) < 0.1:
                print(f"[TARGET] Target acquired! X offset: {x_offset_of_target:.2f}, " 
                      f"Degrees offset: {offset_degrees:.1f}°, Current angle: {self.current_x_angle:.1f}°, "
                      f"Target angle: {self.current_x_angle + offset_degrees:.1f}°")
                time.sleep(0.5)
                continue
            time.sleep(0.5)
        return x_offset_of_target, y_offset_of_target





