import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from utils.log_buffer import get_logs, install_log_capture

install_log_capture()

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

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>raspi-turret</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, sans-serif;
      background: #111;
      color: #eee;
      margin: 0;
      padding: 1rem;
    }
    h1 { margin: 0 0 0.5rem; font-size: 1.25rem; }
    .sub { color: #888; margin-bottom: 1rem; font-size: 0.9rem; }
    .layout {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      align-items: start;
    }
    @media (max-width: 900px) {
      .layout { grid-template-columns: 1fr; }
    }
    .panel {
      border: 1px solid #333;
      border-radius: 6px;
      overflow: hidden;
      background: #1a1a1a;
    }
    .panel h2 {
      margin: 0;
      padding: 0.5rem 0.75rem;
      font-size: 0.85rem;
      background: #222;
      border-bottom: 1px solid #333;
      color: #aaa;
    }
    .video-wrap img {
      display: block;
      width: 100%;
      height: auto;
    }
    .log-wrap {
      display: flex;
      flex-direction: column;
      max-height: 70vh;
    }
    .log-table-wrap {
      overflow: auto;
      flex: 1;
      font-family: ui-monospace, monospace;
      font-size: 0.75rem;
    }
    table.log-table {
      width: 100%;
      border-collapse: collapse;
    }
    .log-table th {
      position: sticky;
      top: 0;
      background: #252525;
      text-align: left;
      padding: 0.35rem 0.5rem;
      color: #888;
      font-weight: 600;
    }
    .log-table td {
      padding: 0.2rem 0.5rem;
      border-top: 1px solid #2a2a2a;
      vertical-align: top;
    }
    .log-table tr:hover td { background: #222; }
    .col-time { color: #6af; white-space: nowrap; width: 7rem; }
    .col-msg { word-break: break-word; }
    .level-error .col-msg { color: #f66; }
    .level-warn .col-msg { color: #fa6; }
    .level-target .col-msg { color: #6f6; }
    .level-info .col-msg { color: #adf; }
    .level-muted .col-msg { color: #666; }
    a { color: #6cf; }
  </style>
</head>
<body>
  <h1>raspi-turret</h1>
  <p class="sub">LAN only — live stream + captured logs</p>
  <div class="layout">
    <div class="panel video-wrap">
      <h2>Live video</h2>
      <img src="/video" alt="live stream">
    </div>
    <div class="panel log-wrap">
      <h2>Logs</h2>
      <div class="log-table-wrap">
        <table class="log-table">
          <thead>
            <tr><th>Time</th><th>Message</th></tr>
          </thead>
          <tbody id="log-body"></tbody>
        </table>
      </div>
    </div>
  </div>
  <p style="margin-top:1rem">
    <a href="/api/status">/api/status</a> ·
    <a href="/api/logs">/api/logs</a>
  </p>
  <script>
    const logBody = document.getElementById('log-body');
    const logWrap = document.querySelector('.log-table-wrap');
    let lastId = 0;
    let autoScroll = true;

    logWrap.addEventListener('scroll', () => {
      const nearBottom = logWrap.scrollHeight - logWrap.scrollTop - logWrap.clientHeight < 40;
      autoScroll = nearBottom;
    });

    function rowClass(level) {
      return level ? 'level-' + level : '';
    }

    function appendEntries(entries) {
      for (const e of entries) {
        const tr = document.createElement('tr');
        tr.className = rowClass(e.level);
        tr.innerHTML = '<td class="col-time">' + e.t + '</td><td class="col-msg"></td>';
        tr.querySelector('.col-msg').textContent = e.msg;
        logBody.appendChild(tr);
        lastId = e.id;
      }
      while (logBody.children.length > 400) {
        logBody.removeChild(logBody.firstChild);
      }
      if (autoScroll) {
        logWrap.scrollTop = logWrap.scrollHeight;
      }
    }

    async function pollLogs() {
      try {
        const res = await fetch('/api/logs?after=' + lastId);
        const data = await res.json();
        if (data.entries && data.entries.length) {
          appendEntries(data.entries);
        }
      } catch (err) {
        console.error(err);
      }
    }

    setInterval(pollLogs, 500);
    pollLogs();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML


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


@app.get("/api/logs")
async def logs(after: int = Query(0, ge=0)):
    return {"entries": get_logs(after)}


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
