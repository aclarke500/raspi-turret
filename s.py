import RPi.GPIO as GPIO
import time

SERVO_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(7.5)  # start at neutral

try:
    while True:
        print("0°")
        pwm.ChangeDutyCycle(2.5)
        time.sleep(1.2)

        print("90°")
        pwm.ChangeDutyCycle(7.5)
        time.sleep(1.2)

        print("180°")
        pwm.ChangeDutyCycle(12.5)
        time.sleep(1.2)

except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()