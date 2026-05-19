#!/usr/bin/env python3
"""
Hold pan at 90° for 10s — listen for buzzing (release pulse should reduce jitter).

Run from repo root:
  python hardware_tests/servo_hold_test.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import RPi.GPIO as GPIO

from utils.servo_config import PAN_MAX_ANGLE, RELEASE_PULSE_AFTER_MOVE, X_SERVO_PIN
from utils.servo_driver import create_driver

HOLD_ANGLE = 0
HOLD_SEC = 10.0

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

print(f"[INIT] release_pulse_after_move={RELEASE_PULSE_AFTER_MOVE}")
driver = create_driver(X_SERVO_PIN, 0, PAN_MAX_ANGLE)
driver.start()

try:
    print(f"[MOVE] Moving to {HOLD_ANGLE}°...")
    driver.set_angle(HOLD_ANGLE)
    print(f"[HOLD] Holding at {driver.current_angle:.1f}° for {HOLD_SEC}s — listen for buzz")
    time.sleep(HOLD_SEC)
    print("[DONE] If servo buzzed continuously, try RELEASE_PULSE_AFTER_MOVE=True in servo_config")
finally:
    driver.stop()
    GPIO.cleanup()
