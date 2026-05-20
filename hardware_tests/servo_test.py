import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from raspi_turret.config.servo import PAN_MAX_ANGLE, X_SERVO_PIN
from raspi_turret.hardware.gpio import GpioBoard
from raspi_turret.hardware.servo import ServoMotor

print("[INIT] Pan servo bench test (release-pulse enabled via servo_config)")
board = GpioBoard()
board.setup()
motor = ServoMotor(X_SERVO_PIN, 0, PAN_MAX_ANGLE, board, name="pan")
motor.start()

try:
    print("[RUN] Sweep 0° → 90° → 180°...")
    while True:
        for angle in (0, 90, 180):
            moved = motor.set_angle(angle)
            print(
                f"[MOVE] angle={angle}° moved={moved} "
                f"current={motor.current_angle:.1f}°"
            )
            time.sleep(1)
except KeyboardInterrupt:
    print("[EXIT] CTRL+C received")
finally:
    motor.stop()
    board.cleanup()
    print("[CLEANUP] Done.")
