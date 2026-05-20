"""Camera abstraction: USB OpenCV and Pi CSI (picamera2)."""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime

import cv2
import numpy as np

from raspi_turret.config.camera import (
    CAMERA_BACKEND,
    DEBUG_FRAME_DIFF,
    DIFF_SAMPLE_SIZE,
    MIN_FRAME_DIFF,
    apply_frame_transform,
    format_timestamp,
)

FRAME_SIZE = (1280, 720)
WARMUP_FRAMES = 10
MIN_FRAME_MEAN = 5.0


class Camera(ABC):
    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def get_frame(self) -> np.ndarray | None:
        ...

    def get_frame_with_capture_time(self) -> tuple[np.ndarray | None, str | None]:
        frame = self.get_frame()
        if frame is None:
            return None, None
        return frame, format_timestamp(datetime.now())


class _FrameBufferMixin:
    """Shared locked frame buffer and optional stale-frame debug."""

    def __init__(self):
        self._frame_lock = threading.Lock()
        self._current_frame: np.ndarray | None = None
        self._current_frame_captured_at: str | None = None
        self._capture_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_small_frame: np.ndarray | None = None
        self._last_stale_log_time = 0.0

    def _check_frame_diff(self, resized: np.ndarray) -> float | None:
        small = cv2.resize(resized, DIFF_SAMPLE_SIZE)
        if self._last_small_frame is None:
            self._last_small_frame = small.copy()
            return None

        diff = np.abs(
            small.astype(np.int16) - self._last_small_frame.astype(np.int16)
        ).mean()
        self._last_small_frame = small.copy()
        return float(diff)

    def _store_frame(self, resized: np.ndarray) -> None:
        if DEBUG_FRAME_DIFF:
            diff = self._check_frame_diff(resized)
            if diff is not None and diff < MIN_FRAME_DIFF:
                now = time.monotonic()
                if now - self._last_stale_log_time >= 1.0:
                    self._last_stale_log_time = now
                    print(
                        f"[WARN] Frame barely changed, mean diff={diff:.2f} "
                        f"(threshold {MIN_FRAME_DIFF})"
                    )

        captured_at = format_timestamp(datetime.now())
        with self._frame_lock:
            self._current_frame = resized.copy()
            self._current_frame_captured_at = captured_at

    def get_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            return (
                self._current_frame.copy()
                if self._current_frame is not None
                else None
            )

    def get_frame_with_capture_time(
        self,
    ) -> tuple[np.ndarray | None, str | None]:
        with self._frame_lock:
            if self._current_frame is None:
                return None, None
            return self._current_frame.copy(), self._current_frame_captured_at

    def _start_capture_thread(self, target):
        self._stop_event.clear()
        self._capture_thread = threading.Thread(target=target, daemon=True)
        self._capture_thread.start()

    def _stop_capture_thread(self):
        self._stop_event.set()
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None


class UsbCamera(_FrameBufferMixin, Camera):
    def __init__(self, device_index: int = 0, frame_size: tuple[int, int] = FRAME_SIZE):
        super().__init__()
        self._device_index = device_index
        self._frame_size = frame_size
        self._cap: cv2.VideoCapture | None = None

    def start(self) -> None:
        if self._capture_thread is not None and self._capture_thread.is_alive():
            return

        self._cap = cv2.VideoCapture(self._device_index)
        if not self._cap.isOpened():
            print(f"[ERROR] Could not open camera (device index {self._device_index})")
            return

        print(f"[INIT] Warming up USB camera ({WARMUP_FRAMES} frames)...")
        for _ in range(WARMUP_FRAMES):
            ret, _ = self._cap.read()
            if not ret:
                print("[WARN] Frame capture failed during warmup")
                time.sleep(0.1)

        self._start_capture_thread(self._capture_loop)

    def stop(self) -> None:
        self._stop_capture_thread()
        if self._cap is not None:
            print("[EXIT] Releasing USB camera")
            self._cap.release()
            self._cap = None

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._cap is None:
                time.sleep(0.1)
                continue

            ret, frame = self._cap.read()
            if ret:
                resized = apply_frame_transform(
                    cv2.resize(frame, self._frame_size)
                )
                if resized.mean() < MIN_FRAME_MEAN:
                    time.sleep(0.05)
                    continue
                self._store_frame(resized)
            else:
                print("[WARN] Frame capture failed")
                time.sleep(0.1)


class PiCamera(_FrameBufferMixin, Camera):
    """Raspberry Pi CSI camera via picamera2 (Pi only)."""

    def __init__(self, frame_size: tuple[int, int] = FRAME_SIZE):
        super().__init__()
        self._frame_size = frame_size
        self._picam2 = None

    def start(self) -> None:
        if self._capture_thread is not None and self._capture_thread.is_alive():
            return

        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise RuntimeError(
                "picamera2 not installed. On the Pi run: sudo apt install -y python3-picamera2"
            ) from exc

        info = Picamera2.global_camera_info()
        if not info:
            raise RuntimeError(
                "No libcamera cameras found. Enable CSI in raspi-config and check cable."
            )

        for cam in info:
            print(
                f"[INIT] libcamera device id={cam.get('Num', '?')} "
                f"model={cam.get('Model', '?')}"
            )

        self._picam2 = Picamera2()
        config = self._picam2.create_preview_configuration(
            main={"size": self._frame_size, "format": "RGB888"}
        )
        self._picam2.configure(config)
        self._picam2.start()

        print(f"[INIT] Warming up Pi camera ({WARMUP_FRAMES} frames)...")
        for i in range(WARMUP_FRAMES):
            self._picam2.capture_array()
            if i == 0:
                time.sleep(0.2)

        self._start_capture_thread(self._capture_loop)

    def stop(self) -> None:
        self._stop_capture_thread()
        if self._picam2 is not None:
            try:
                self._picam2.stop()
            except Exception:
                pass
            self._picam2 = None
            print("[EXIT] Pi camera stopped")

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._picam2 is None:
                time.sleep(0.1)
                continue

            try:
                rgb = self._picam2.capture_array()
                if rgb is None or rgb.size == 0:
                    time.sleep(0.1)
                    continue
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                resized = apply_frame_transform(cv2.resize(bgr, self._frame_size))
                if resized.mean() < MIN_FRAME_MEAN:
                    time.sleep(0.05)
                    continue
                self._store_frame(resized)
            except Exception as e:
                print(f"[WARN] Pi camera capture failed: {e}")
                time.sleep(0.1)


def create_camera(
    backend: str | None = None,
    *,
    device_index: int = 0,
) -> Camera:
    backend = (backend or CAMERA_BACKEND).lower().strip()
    if backend == "pi":
        return PiCamera()
    if backend == "usb":
        return UsbCamera(device_index=device_index)
    raise ValueError(f"Unknown CAMERA_BACKEND {backend!r}; use 'usb' or 'pi'")
