from PIL import Image
import numpy as np
import tflite_runtime.interpreter as tflite
from pathlib import Path
import subprocess
import time
import RPi.GPIO as GPIO


# Pin config
SERVO_PIN = 17  # GPIO 17 = Physical pin 11

print("[INIT] Setting up GPIO mode...")
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

print("[INIT] Starting PWM on pin 17 at 50Hz (20ms period)...")
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for servo control
pwm.start(0)  # initial duty cycle



# set up tflite
model_path = str(Path.home() / "tflite_models" / "detect.tflite")
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()



def set_angle(angle):
    # Convert angle (0–180) to duty cycle
    duty = (0.05 * angle) + 2.5
    print(f"[MOVE] Setting angle to {angle}°, which maps to duty cycle {duty:.2f}%")
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    print("[MOVE] Killing PWM duty to reduce jitter")
    # pwm.ChangeDutyCycle(0)


def get_target_direction():
    try:
        # take photo
        subprocess.run(
            "SIZE=1280x720 FPS=30 bash photo.sh /dev/video0",
            shell=True, check=True
        )

        img = Image.open("test.jpg").resize((300, 300))
        input_data = np.expand_dims(np.array(img, dtype=np.uint8), axis=0)

        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()

        boxes = interpreter.get_tensor(output_details[0]['index'])[0]
        classes = interpreter.get_tensor(output_details[1]['index'])[0]
        scores = interpreter.get_tensor(output_details[2]['index'])[0]

        with open(Path.home() / "tflite_models" / "coco_labels.txt") as f:
            labels = f.read().splitlines()
        
        # open image again to get original size
        orig_img = Image.open("test.jpg")
        width, height = orig_img.size
        target = (width / 2, height / 2)

        for i in range(len(scores)):
            if scores[i] > 0.5 and labels[int(classes[i])] == "person":
                ymin, xmin, ymax, xmax = boxes[i]
                
                # scale bounding box to pixel coordinates
                left = int(xmin * width)
                top = int(ymin * height)
                right = int(xmax * width)
                bottom = int(ymax * height)

                # compute center of the bounding box
                person_center = ((left + right) / 2, (top + bottom) / 2)

                # compute vector from target to person center
                vector = (person_center[0] - target[0], person_center[1] - target[1])

                x_normalized = vector[0] / (width / 2)
                print(x_normalized)
                return x_normalized

        return None  # No person found
    except Exception as e:
        print(f"[ERROR] get_target_direction failed: {e}")
        return None

base = 135
set_angle(base)
for i in range(1000):
    x=get_target_direction()
    if x is not None:
        angle = base + (x * 45)
        set_angle(angle)
