from dataclasses import dataclass
from pathlib import Path
import threading
import time

import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

from utils.camera import get_current_frame

model_path = str(Path.home() / "tflite_models" / "detect.tflite")
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

with open(Path.home() / "tflite_models" / "coco_labels.txt") as f:
    labels = f.read().splitlines()

PERSON_SCORE_THRESHOLD = 0.5
_inference_lock = threading.Lock()


@dataclass
class DetectionResult:
    x_norm: float
    y_norm: float
    left: int
    top: int
    right: int
    bottom: int
    score: float


def detect_person(frame) -> DetectionResult | None:
    if frame is None:
        return None

    img_resized = cv2.resize(frame, (300, 300))
    input_data = np.expand_dims(img_resized.astype(np.uint8), axis=0)

    with _inference_lock:
        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()
        boxes = interpreter.get_tensor(output_details[0]["index"])[0].copy()
        classes = interpreter.get_tensor(output_details[1]["index"])[0].copy()
        scores = interpreter.get_tensor(output_details[2]["index"])[0].copy()

    height, width, _ = frame.shape
    center_x = width / 2
    center_y = height / 2

    for i in range(len(scores)):
        if scores[i] > PERSON_SCORE_THRESHOLD and labels[int(classes[i])] == "person":
            ymin, xmin, ymax, xmax = boxes[i]

            left = int(xmin * width)
            top = int(ymin * height)
            right = int(xmax * width)
            bottom = int(ymax * height)

            person_center = ((left + right) / 2, (top + bottom) / 2)
            vector = (person_center[0] - center_x, person_center[1] - center_y)
            x_normalized = vector[0] / (width / 2)
            y_normalized = vector[1] / (height / 2)

            return DetectionResult(
                x_norm=x_normalized,
                y_norm=y_normalized,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                score=float(scores[i]),
            )

    return None


def annotate_frame(frame, result: DetectionResult | None):
    annotated = frame.copy()
    height, width, _ = annotated.shape
    center = (int(width / 2), int(height / 2))

    cv2.drawMarker(
        annotated,
        center,
        (0, 255, 255),
        markerType=cv2.MARKER_CROSS,
        markerSize=24,
        thickness=2,
    )

    if result is None:
        cv2.putText(
            annotated,
            "NO_PERSON",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )
        return annotated

    cv2.rectangle(
        annotated,
        (result.left, result.top),
        (result.right, result.bottom),
        (0, 255, 0),
        2,
    )
    label = (
        f"person {result.score:.2f}  "
        f"x={result.x_norm:+.2f} y={result.y_norm:+.2f}"
    )
    cv2.putText(
        annotated,
        label,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    return annotated


def get_target_direction():
    try:
        time.sleep(0.05)
        print("Trying to get frame")
        frame = get_current_frame()
        if frame is None:
            return None, None

        result = detect_person(frame)
        if result is None:
            return None, None

        print("found person")
        print(f"x_normalized: {result.x_norm}, y_normalized: {result.y_norm}  ")
        return result.x_norm, result.y_norm
    except Exception as e:
        print(f"[ERROR] get_target_direction failed: {e}")
        return None, None


def is_in_safezone(x):
    degrees = 135 * abs(x)
    not_valid = degrees <= 20
    if not_valid:
        print("not valid: ", degrees, " degrees.")
    return degrees <= 20
