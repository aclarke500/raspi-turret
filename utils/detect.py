from PIL import Image
import numpy as np
import tflite_runtime.interpreter as tflite
from pathlib import Path
import subprocess
import time
import RPi.GPIO as GPIO
from utils.camera import get_current_frame

import cv2


# # Pin config
# SERVO_PIN = 17  # GPIO 17 = Physical pin 11

# print("[INIT] Setting up GPIO mode...")
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(SERVO_PIN, GPIO.OUT)

# print("[INIT] Starting PWM on pin 17 at 50Hz (20ms period)...")
# pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for servo control
# pwm.start(0)  # initial duty cycle



# set up tflite
model_path = str(Path.home() / "tflite_models" / "detect.tflite")
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()


with open(Path.home() / "tflite_models" / "coco_labels.txt") as f:
    labels = f.read().splitlines()
def get_target_direction():
    try:
        time.sleep(0.05)
        print('Trying to get frame')
        frame = get_current_frame()
        # Resize to model input shape
        img_resized = cv2.resize(frame, (300, 300))
        input_data = np.expand_dims(img_resized.astype(np.uint8), axis=0)

        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()

        boxes = interpreter.get_tensor(output_details[0]['index'])[0]
        classes = interpreter.get_tensor(output_details[1]['index'])[0]
        scores = interpreter.get_tensor(output_details[2]['index'])[0]

        height, width, _ = frame.shape
        target = (width / 2, height / 2)

        for i in range(len(scores)):
            if scores[i] > 0.5 and labels[int(classes[i])] == "person":
                print('found person')
                ymin, xmin, ymax, xmax = boxes[i]

                left = int(xmin * width)
                top = int(ymin * height)
                right = int(xmax * width)
                bottom = int(ymax * height)

                person_center = ((left + right) / 2, (top + bottom) / 2)

                vector = (person_center[0] - target[0], person_center[1] - target[1])
                x_normalized = vector[0] / (width / 2)
                y_normalized = vector[1] / (height / 2)
                print(f"x_normalized: {x_normalized}, y_normalized: {y_normalized}  ")
                return x_normalized, y_normalized

        return None, None
    except Exception as e:
        print(f"[ERROR] get_target_direction failed: {e}")
        return None, None

def is_in_safezone(x):
    degrees = 135 * abs(x)
    not_valid = degrees <= 20
    if not_valid:
        print("not valid: ", degrees, " degrees.")
    return degrees <= 20

