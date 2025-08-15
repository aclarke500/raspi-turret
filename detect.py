from PIL import Image
import numpy as np
import tflite_runtime.interpreter as tflite
from pathlib import Path
import subprocess
import time


# set up tflite
model_path = str(Path.home() / "tflite_models" / "detect.tflite")
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def get_target_direction():
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

            print(f"Detected PERSON with {scores[i]*100:.1f}% confidence")
            print(f"Bounding box: ({left}, {top}) to ({right}, {bottom})")
            print(f"Center of person: {person_center}")
            print(f"Vector from target {target} to person: {vector}")



for i in range(10):
    get_target_direction()
    time.sleep(0)
