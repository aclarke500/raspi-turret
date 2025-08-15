import RPi.GPIO as GPIO
import time

LED_PIN = 17  # GPIO17 = pin 11

print("[INIT] Setting up GPIO output...")
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

try:
    print("[RUN] Blinking LED on/off every 0.25 seconds...")
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)
        print("[LED] ON")
        time.sleep(0.25)
        GPIO.output(LED_PIN, GPIO.LOW)
        print("[LED] OFF")
        time.sleep(0.25)

except KeyboardInterrupt:
    print("[EXIT] Cleaning up GPIO...")
    GPIO.cleanup()
