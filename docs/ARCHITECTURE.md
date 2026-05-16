# raspi-turret — architecture & bring-up

Companion to the root [README.md](../README.md). Use this to remember how the code fits together after time away from the project.

**Pi deploy path:** `/home/aclarke500/Desktop/tflite-prac`

---

## What this does (today)

1. Capture video from a **USB webcam** (1280×720) in a background thread.
2. While the **X servo** patrols 0° → 270° → 0°, run person detection on each stop.
3. When a person is seen, **snap_to_target** iteratively pans until the target is near the center of the frame.

**X-only tracking in practice:** Y servo PWM is initialized, but `set_y_angle()` returns immediately (disabled). **No fire/trigger GPIO exists in code yet.**

---

## Rewiring checklist (nothing connected right now)

When you reconnect hardware, use **BCM** pin numbers (what the code uses).

| Function | BCM GPIO | Physical pin (40-pin header) | Wire to |
|----------|----------|-------------------------------|---------|
| X servo signal (pan) | **17** | **11** | Servo signal (orange/yellow) |
| Y servo signal (tilt) | **27** | **13** | Servo signal |
| Servo power | — | **2 or 4** (5V) | Prefer **external 5V** for two servos; share GND with Pi |
| Servo ground | — | **6, 9, 14, 20, 25, 30, 34, or 39** (GND) | Servo GND + supply GND |
| USB webcam | — | Any USB port | Should appear as `/dev/video0` |

**PWM settings (from code):** 50 Hz, duty cycle `(0.05 × angle) + 2.5`, angle clamped **0–270°** on X.

**Before powering on:** Do not run `led_test.py` while the X servo is on GPIO 17 — that script uses the same pin as a digital output.

---

## File map

| File | Role |
|------|------|
| `main.py` | **Production entry point.** Loop: `patrol()` → if target, `snap_to_target()`. SIGINT/SIGTERM → `T.cleanup()`. |
| `Turret.py` | `Turret` class: PWM pan/tilt, `patrol()`, `snap_to_target()`. **Also runs GPIO init at import time** (see caveats). |
| `utils/camera.py` | OpenCV `VideoCapture(0)`, background thread, `get_current_frame()`. |
| `utils/detect.py` | TFLite SSD model, `get_target_direction()` → normalized (x, y) offset or `(None, None)`. |
| `utils/utils.py` | `x_offset_to_degrees` / `y_offset_to_degrees` from assumed 55° diagonal FOV, 16:9. |
| `coco_labels.txt` | COCO class names — copy to `~/tflite_models/` per root README. |
| `requirements.txt` | numpy, opencv-python-headless, pillow, tflite-runtime. |
| `hardware_tests/servo_test.py` | Bench test: GPIO 17 servo 0° / 90° / 180°. |
| `hardware_tests/camera_test.py` | Bench test: 10 OpenCV frames → `test_photos/frame_01.jpg` … (1280×720, 0.1s apart). |
| `hardware_tests/ai_test.py` | Bench test: `get_target_direction()` loop up to 5 min (Ctrl+C to stop) — normalized (x, y) from frame center. |
| `calibrate_y_motor.py` | Bench test: GPIO 27 sweep 0–270°. |
| `led_test.py` | Blink GPIO 17 — conflicts with X servo on same pin. |
| `s.py` | Alternative servo test using **pigpio** on GPIO 17. |
| `compute_fov.py` | Standalone print of horizontal/vertical FOV from diagonal FOV. |
| `photo.sh` | Legacy: grab one frame via ffmpeg → `test.jpg`. |
| `main.sh` | Legacy: `photo.sh` + `python detect.py`. |
| `detect.py` (repo root) | **Fully commented out** — old snapshot + detect path. |
| `utils/servo.py` | Standalone GPIO 17 helper; **not used** by `main.py`. |

---

## Code dependency diagram

```mermaid
flowchart TB
    subgraph entry["Entry"]
        main["main.py"]
    end

    subgraph turret_mod["Turret.py (import side effects)"]
        TurretClass["class Turret"]
        GPIOInit["GPIO + PWM init\n(GPIO 17, 27)"]
    end

    subgraph utils_pkg["utils/"]
        detect["detect.py\nget_target_direction()"]
        camera["camera.py\nget_current_frame()"]
        ut["utils.py\nx_offset_to_degrees()"]
    end

    subgraph external["External / system"]
        tflite["~/tflite_models/detect.tflite"]
        labels["~/tflite_models/coco_labels.txt"]
        webcam["/dev/video0 via OpenCV"]
        gpio["RPi.GPIO PWM"]
    end

    main --> TurretClass
    main --> ut
    TurretClass --> detect
    TurretClass --> ut
    TurretClass --> gpio
    GPIOInit --> gpio
    detect --> camera
    detect --> tflite
    detect --> labels
    camera --> webcam
```

**Import note:** `from Turret import Turret` runs **all top-level code** in `Turret.py` (GPIO setup, signal handlers) before `main.py` calls `T.setup()`.

---

## Happy path (runtime)

```mermaid
sequenceDiagram
    participant User
    participant main as main.py
    participant T as Turret
    participant Cam as utils/camera
    participant Det as utils/detect

    User->>main: python main.py
    Note over Cam: Background capture thread starts when detect/camera loads
    main->>T: Turret(); setup() → pan to 0,0

    loop Forever
        main->>T: patrol()
        loop Sweep X 0..270..0
            T->>T: set_x_angle(angle)
            T->>Det: get_target_direction()
            Det->>Cam: get_current_frame()
            Det->>Det: TFLite infer "person"
            alt person found
                Det-->>T: x_norm, y_norm
                T-->>main: offsets
            end
        end

        alt target seen
            main->>main: x_offset_to_degrees()
            main->>T: snap_to_target(deg_x, deg_y)
            loop up to 100 iterations
                T->>T: set_x_angle(current + offset)
                Note over T: set_y_angle() no-op (disabled)
                T->>Det: get_target_direction()
            end
        end
    end

    User->>main: Ctrl+C
    main->>T: cleanup()
```

### Prerequisites (on the Pi)

1. Raspberry Pi OS with `RPi.GPIO` and `tflite_runtime` available.
2. Python venv + dependencies (see root README and `requirements.txt`).
3. Model at `~/tflite_models/detect.tflite` and labels at `~/tflite_models/coco_labels.txt`.
4. USB webcam on `/dev/video0` (OpenCV device index `0`).
5. Servos rewired per table above.

### Run

```bash
cd /home/aclarke500/Desktop/tflite-prac
source venv/bin/activate   # if you use a venv
python main.py
```

### Bench hardware before full stack

```bash
python hardware_tests/servo_test.py    # X axis only (GPIO 17)
python hardware_tests/camera_test.py   # USB webcam burst to test_photos/
python hardware_tests/ai_test.py       # person detect; prints center-relative x, y
python calibrate_y_motor.py            # Y axis only (GPIO 27)
```

---

## Detection pipeline

1. `utils/camera.py` continuously reads and resizes to **1280×720**.
2. `get_target_direction()` resizes the frame to **300×300** and runs TFLite.
3. Keeps detections with `score > 0.5` and COCO label `"person"`.
4. Returns offset normalized to roughly ±1 relative to frame center:
   - `x_normalized = (person_cx - center_x) / (width / 2)`
   - same pattern for Y
5. `x_offset_to_degrees(x) = -x * hfov / 2` where hfov ≈ 48.5° (from 55° diagonal, 16:9 in `utils/utils.py`).

---

## Legacy path (superseded)

Older flow used still frames instead of live video:

1. `photo.sh` — ffmpeg grabs one image → `test.jpg`
2. `main.sh` — runs `photo.sh` then `python detect.py`
3. Root `detect.py` — **entirely commented out**; was the old detect + servo experiment

Current production path uses `utils/camera.py` + `utils/detect.py` only.

---

## Known quirks / tech debt

1. **GPIO init on import** in `Turret.py` — importing the module configures pins and registers signal handlers; can warn if GPIO is already in use.
2. **Duplicate signal handlers** — both `Turret.py` and `main.py` register SIGINT/SIGTERM.
3. **Y axis disabled** — remove the early `return` in `set_y_angle()` to enable tilt tracking.
4. **`utils/detect.py` imports `RPi.GPIO` unused** (leftover).
5. **`requirements.txt` omits `RPi.GPIO`** — install on the Pi when setting up the venv.
6. **Shooting** — described in the project README as a goal; not implemented in GPIO or Python yet.

---

## Raspberry Pi 40-pin header (quick reference)

```
     3V3  (1) (2)  5V
   GPIO2  (3) (4)  5V
   GPIO3  (5) (6)  GND
   GPIO4  (7) (8)  GPIO14
     GND  (9) (10) GPIO15
  GPIO17  (11) (12) GPIO18   ← X servo signal (pin 11)
  GPIO27  (13) (14) GND      ← Y servo signal (pin 13)
  ...
```

BCM **17** = physical **11**, BCM **27** = physical **13**.
