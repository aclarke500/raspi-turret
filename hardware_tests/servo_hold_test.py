import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from raspi_turret.config.servo import PAN_MAX_ANGLE, RELEASE_PULSE_AFTER_MOVE, X_SERVO_PIN
from raspi_turret.hardware.gpio import GpioBoard
from raspi_turret.hardware.servo import ServoMotor

HOLD_ANGLE = 90
HOLD_SEC = 10

print(f"[INIT] Hold test GPIO {X_SERVO_PIN} at {HOLD_ANGLE}° for {HOLD_SEC}s")
print(f"[INIT] RELEASE_PULSE_AFTER_MOVE={RELEASE_PULSE_AFTER_MOVE}")

board = GpioBoard()
board.setup()
motor = ServoMotor(X_SERVO_PIN, 0, PAN_MAX_ANGLE, board, name="pan")
motor.start()

try:
    motor.set_angle(HOLD_ANGLE)
    print(f"[HOLD] At {motor.current_angle:.1f}° — listen for buzzing...")
    time.sleep(HOLD_SEC)
except KeyboardInterrupt:
    print("[EXIT] CTRL+C received")
finally:
    motor.stop()
    board.cleanup()
    print("[CLEANUP] Done.")
