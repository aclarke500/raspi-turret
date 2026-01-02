import pigpio
import time

SERVO_PIN = 17
pi = pigpio.pi()
if not pi.connected:
    exit()

try:
    while True:
        print("[TEST] 0° (500µs)")
        pi.set_servo_pulsewidth(SERVO_PIN, 500)
        time.sleep(1.5)

        print("[TEST] 135° (1500µs)")
        pi.set_servo_pulsewidth(SERVO_PIN, 1500)
        time.sleep(1.5)

        print("[TEST] 270° (2500µs)")
        pi.set_servo_pulsewidth(SERVO_PIN, 2500)
        time.sleep(1.5)

except KeyboardInterrupt:
    pi.set_servo_pulsewidth(SERVO_PIN, 0)
    pi.stop()
    print("[EXIT] Cleaned up.")