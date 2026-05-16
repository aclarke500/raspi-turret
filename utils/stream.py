import threading
import time

import cv2

from utils.camera import get_current_frame
from utils.detect import DetectionResult, annotate_frame, detect_person

STREAM_FPS = 5
STREAM_SIZE = (640, 480)
JPEG_QUALITY = 80


class StreamPublisher:
    def __init__(self):
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._last_detection: DetectionResult | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def fps(self) -> int:
        return STREAM_FPS

    def last_detection(self) -> DetectionResult | None:
        with self._lock:
            return self._last_detection

    def get_jpeg(self) -> bytes | None:
        with self._lock:
            return self._jpeg

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self):
        interval = 1.0 / STREAM_FPS
        while not self._stop_event.is_set():
            frame = get_current_frame()
            if frame is not None:
                result = detect_person(frame)
                annotated = annotate_frame(frame, result)
                resized = cv2.resize(annotated, STREAM_SIZE)
                ok, encoded = cv2.imencode(
                    ".jpg",
                    resized,
                    [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
                )
                if ok:
                    jpeg_bytes = encoded.tobytes()
                    with self._lock:
                        self._jpeg = jpeg_bytes
                        self._last_detection = result

            time.sleep(interval)
