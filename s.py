import RPi.GPIO as GPIO
import time

SERVO_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz
pwm.start(0)  # Start with no pulse

try:
    while True:
        print("[TEST] Moving to 0° (2.5% duty)")
        pwm.ChangeDutyCycle(2.5)  # ~500µs
        time.sleep(1.5)

        print("[TEST] Moving to 135° (7.5% duty - neutral)")
        pwm.ChangeDutyCycle(7.5)  # ~1500µs
        time.sleep(1.5)

        print("[TEST] Moving to 270° (12.5% duty)")
        pwm.ChangeDutyCycle(12.5)  # ~2500µs
        time.sleep(1.5)

except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()
    print("[EXIT] Cleaned up.")