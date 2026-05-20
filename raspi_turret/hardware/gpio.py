"""Shared BCM GPIO setup for all servos on one board."""

import RPi.GPIO as GPIO


class GpioBoard:
    """Initialize GPIO mode once; cleanup releases all pins."""

    def __init__(self):
        self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def setup(self):
        if not self._ready:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            self._ready = True

    def cleanup(self):
        if self._ready:
            GPIO.cleanup()
            self._ready = False
