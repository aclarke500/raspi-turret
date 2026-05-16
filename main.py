import asyncio
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from Turret import Turret
from utils.stream import StreamPublisher
from utils.utils import x_offset_to_degrees

turret: Turret | None = None
stream_publisher: StreamPublisher | None = None
turret_stop_event = threading.Event()
turret_thread: threading.Thread | None = None
turret_running = False


def run_turret_loop(stop_event: threading.Event, turret_instance: Turret):
    global turret_running
    turret_running = True
    try:
        while not stop_event.is_set():
            x_offset, y_offset = turret_instance.patrol()
            if x_offset is not None:
                x_deg = x_offset_to_degrees(x_offset)
                y_deg = x_offset_to_degrees(y_offset)
                turret_instance.snap_to_target(x_deg, y_deg)
    finally:
        turret_running = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global turret, stream_publisher, turret_thread

    turret = Turret()
    turret.setup()

    stream_publisher = StreamPublisher()
    stream_publisher.start()

    turret_stop_event.clear()
    turret_thread = threading.Thread(
        target=run_turret_loop,
        args=(turret_stop_event, turret),
        daemon=True,
    )
    turret_thread.start()

    yield

    turret_stop_event.set()
    if turret_thread is not None:
        turret_thread.join(timeout=5.0)

    if stream_publisher is not None:
        stream_publisher.stop()

    if turret is not None:
        turret.cleanup()


app = FastAPI(title="raspi-turret", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>raspi-turret</title>
  <style>
    body { font-family: sans-serif; background: #111; color: #eee; margin: 1rem; }
    img { max-width: 100%; border: 1px solid #444; }
    a { color: #6cf; }
  </style>
</head>
<body>
  <h1>raspi-turret live view</h1>
  <p>LAN troubleshooting only — no authentication.</p>
  <img src="/video" alt="live stream">
  <p><a href="/api/status">/api/status</a> (JSON)</p>
</body>
</html>
"""


async def mjpeg_generator():
    boundary = b"frame"
    while True:
        if stream_publisher is None:
            await asyncio.sleep(0.2)
            continue

        jpeg = stream_publisher.get_jpeg()
        if jpeg is not None:
            yield (
                b"--" + boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            )
        await asyncio.sleep(1.0 / stream_publisher.fps)


@app.get("/video")
async def video():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/status")
async def status():
    detection = None
    if stream_publisher is not None:
        result = stream_publisher.last_detection()
        if result is not None:
            detection = {
                "x": result.x_norm,
                "y": result.y_norm,
                "score": result.score,
            }

    return {
        "turret_running": turret_running,
        "x_angle": turret.current_x_angle if turret is not None else None,
        "stream_fps": stream_publisher.fps if stream_publisher is not None else None,
        "last_detection": detection,
    }
