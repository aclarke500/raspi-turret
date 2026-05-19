import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import RPi.GPIO as GPIO

from utils.servo_config import PAN_MAX_ANGLE, X_SERVO_PIN, Y_SERVO_PIN
from utils.servo_driver import create_driver

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print("[INIT] Pan servo bench test (release-pulse enabled via servo_config)")
driver = create_driver(Y_SERVO_PIN, 0, PAN_MAX_ANGLE)
driver.start()

try:
    print("[RUN] Sweep 0° → 90° → 180°...")
    while True:
        for angle in (100):
            moved = driver.set_angle(angle)
            print(f"[MOVE] angle={angle}° moved={moved} current={driver.current_angle:.1f}°")
            time.sleep(1)
except KeyboardInterrupt:
    print("[EXIT] CTRL+C received")
finally:
    driver.stop()
    GPIO.cleanup()
    print("[CLEANUP] Done.")
