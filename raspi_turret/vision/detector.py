from dataclasses import dataclass
from pathlib import Path
import threading
import time

import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

from raspi_turret.config.servo import BOX_CENTER_TOLERANCE
from raspi_turret.hardware.camera import Camera

PERSON_SCORE_THRESHOLD = 0.5
MODEL_PATH = Path.home() / "tflite_models" / "detect.tflite"
LABELS_PATH = Path.home() / "tflite_models" / "coco_labels.txt"


@dataclass
class DetectionResult:
    x_norm: float
    y_norm: float
    left: int
    top: int
    right: int
    bottom: int
    score: float
    frame_width: int
    frame_height: int

    def crosshair_inside_box(self) -> bool:
        cx, cy = self.crosshair_xy
        return self.left <= cx <= self.right and self.top <= cy <= self.bottom

    @property
    def box_width(self) -> int:
        return max(1, self.right - self.left)

    @property
    def box_height(self) -> int:
        return max(1, self.bottom - self.top)

    def center_offset_px(
        self, tolerance: float = BOX_CENTER_TOLERANCE
    ) -> tuple[float, float, float, float]:
        ch_x, ch_y = self.crosshair_xy
        cen_x, cen_y = self.centroid_xy
        tol_x = tolerance * self.box_width
        tol_y = tolerance * self.box_height
        return ch_x - cen_x, ch_y - cen_y, tol_x, tol_y

    def is_centered_on_box(self, tolerance: float = BOX_CENTER_TOLERANCE) -> bool:
        dx, dy, tol_x, tol_y = self.center_offset_px(tolerance)
        return abs(dx) <= tol_x and abs(dy) <= tol_y

    @property
    def crosshair_xy(self) -> tuple[float, float]:
        return (self.frame_width / 2, self.frame_height / 2)

    @property
    def centroid_xy(self) -> tuple[float, float]:
        return ((self.left + self.right) / 2, (self.top + self.bottom) / 2)

    @property
    def corners(self) -> dict[str, tuple[int, int]]:
        return {
            "top_left": (self.left, self.top),
            "top_right": (self.right, self.top),
            "bottom_left": (self.left, self.bottom),
            "bottom_right": (self.right, self.bottom),
        }

    def person_horizontal_hint(self) -> str:
        cx, _ = self.crosshair_xy
        px, _ = self.centroid_xy
        if px > cx:
            return "person_right_of_crosshair"
        if px < cx:
            return "person_left_of_crosshair"
        return "person_aligned_horizontally"

    def person_vertical_hint(self) -> str:
        _, cy = self.crosshair_xy
        _, py = self.centroid_xy
        if py > cy:
            return "person_below_crosshair"
        if py < cy:
            return "person_above_crosshair"
        return "person_aligned_vertically"


def log_tracking_debug(
    result: DetectionResult | None,
    *,
    decision: str,
    step_deg: float | None = None,
    step_y_deg: float | None = None,
    pan_angle: float | None = None,
    tilt_angle: float | None = None,
    detail: str = "",
) -> None:
    if result is None:
        parts = [f"[TRACK] decision={decision}"]
        if detail:
            parts.append(f"detail={detail}")
        print(" ".join(parts))
        return

    ch_x, ch_y = result.crosshair_xy
    cen_x, cen_y = result.centroid_xy
    c = result.corners
    dx, dy, tol_x, tol_y = result.center_offset_px()
    centered = result.is_centered_on_box()
    step_s = "None" if step_deg is None else f"{step_deg:+.1f}"
    step_y_s = "None" if step_y_deg is None else f"{step_y_deg:+.1f}"
    pan_s = "None" if pan_angle is None else f"{pan_angle:.1f}"
    tilt_s = "None" if tilt_angle is None else f"{tilt_angle:.1f}"

    parts = [
        f"[TRACK] decision={decision}",
        f"crosshair=({ch_x:.0f},{ch_y:.0f})",
        f"centroid=({cen_x:.0f},{cen_y:.0f})",
        f"centered={centered}",
        f"offset_px=({dx:+.0f},{dy:+.0f})",
        f"tol_px=({tol_x:.0f},{tol_y:.0f})",
        f"corners=TL{c['top_left']} TR{c['top_right']} BL{c['bottom_left']} BR{c['bottom_right']}",
        f"x_norm={result.x_norm:+.2f} y_norm={result.y_norm:+.2f}",
        f"score={result.score:.2f}",
        result.person_horizontal_hint(),
        result.person_vertical_hint(),
        f"step_pan={step_s}",
        f"step_tilt={step_y_s}",
        f"pan={pan_s}°",
        f"tilt={tilt_s}°",
    ]
    if detail:
        parts.append(f"detail={detail}")
    print(" ".join(parts))


class PersonDetector:
    """TFLite SSD person detector; lazy-loads model on first use."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        labels_path: str | Path | None = None,
    ):
        self._model_path = Path(model_path or MODEL_PATH)
        self._labels_path = Path(labels_path or LABELS_PATH)
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self._labels: list[str] = []
        self._inference_lock = threading.Lock()
        self._invalid_class_log_time = 0.0
        self._load_lock = threading.Lock()

    def _ensure_loaded(self):
        if self._interpreter is not None:
            return
        with self._load_lock:
            if self._interpreter is not None:
                return
            print(f"[INIT] Loading TFLite model {self._model_path}...")
            interpreter = tflite.Interpreter(model_path=str(self._model_path))
            interpreter.allocate_tensors()
            with open(self._labels_path) as f:
                labels = [
                    line.strip() for line in f.read().splitlines() if line.strip()
                ]
            self._interpreter = interpreter
            self._input_details = interpreter.get_input_details()
            self._output_details = interpreter.get_output_details()
            self._labels = labels

    def _class_to_label(self, class_id) -> str | None:
        idx = int(class_id)
        if 1 <= idx <= len(self._labels):
            return self._labels[idx - 1]
        if 0 <= idx < len(self._labels):
            return self._labels[idx]
        return None

    def detect(self, frame) -> DetectionResult | None:
        self._ensure_loaded()

        if frame is None:
            return None

        try:
            img_resized = cv2.resize(frame, (300, 300))
            input_data = np.expand_dims(img_resized.astype(np.uint8), axis=0)

            with self._inference_lock:
                self._interpreter.set_tensor(
                    self._input_details[0]["index"], input_data
                )
                self._interpreter.invoke()
                boxes = self._interpreter.get_tensor(
                    self._output_details[0]["index"]
                )[0].copy()
                classes = self._interpreter.get_tensor(
                    self._output_details[1]["index"]
                )[0].copy()
                scores = self._interpreter.get_tensor(
                    self._output_details[2]["index"]
                )[0].copy()

            height, width, _ = frame.shape
            center_x = width / 2
            center_y = height / 2

            best: DetectionResult | None = None

            for i in range(len(scores)):
                if scores[i] <= PERSON_SCORE_THRESHOLD:
                    continue

                label = self._class_to_label(classes[i])
                if label is None:
                    now = time.monotonic()
                    if now - self._invalid_class_log_time >= 5.0:
                        self._invalid_class_log_time = now
                        print(
                            f"[WARN] Ignoring detection class id {int(classes[i])} "
                            f"(out of range for {len(self._labels)} COCO labels; not an error). "
                            f"Valid person id is 1."
                        )
                    continue
                if label != "person":
                    continue

                ymin, xmin, ymax, xmax = boxes[i]

                left = int(xmin * width)
                top = int(ymin * height)
                right = int(xmax * width)
                bottom = int(ymax * height)

                person_center = ((left + right) / 2, (top + bottom) / 2)
                vector = (
                    person_center[0] - center_x,
                    person_center[1] - center_y,
                )
                x_normalized = vector[0] / (width / 2)
                y_normalized = vector[1] / (height / 2)

                candidate = DetectionResult(
                    x_norm=x_normalized,
                    y_norm=y_normalized,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    score=float(scores[i]),
                    frame_width=width,
                    frame_height=height,
                )
                if best is None or candidate.score > best.score:
                    best = candidate

            return best
        except Exception as e:
            print(f"[ERROR] detect failed: {e}")
            return None

    def detect_latest(self, camera: Camera) -> DetectionResult | None:
        try:
            time.sleep(0.05)
            frame = camera.get_frame()
            return self.detect(frame)
        except Exception as e:
            print(f"[ERROR] detect_latest failed: {e}")
            return None

    def get_target_direction(self, camera: Camera):
        result = self.detect_latest(camera)
        if result is None:
            return None, None
        return result.x_norm, result.y_norm


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
    centered = result.is_centered_on_box()
    label = (
        f"person {result.score:.2f}  "
        f"x={result.x_norm:+.2f} y={result.y_norm:+.2f}  "
        f"{'CENTERED' if centered else 'TRACK'}"
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
