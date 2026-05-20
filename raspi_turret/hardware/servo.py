"""Domain-level servo motor: pin, angle bounds, start/stop lifecycle."""

from raspi_turret.hardware.drivers import create_driver
from raspi_turret.hardware.gpio import GpioBoard


class ServoMotor:
    def __init__(
        self,
        pin: int,
        min_angle: float,
        max_angle: float,
        board: GpioBoard,
        *,
        name: str = "servo",
    ):
        self._pin = pin
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._board = board
        self._name = name
        self._driver = None
        self._started = False

    @property
    def current_angle(self) -> float:
        if self._driver is None:
            return self._min_angle
        return self._driver.current_angle

    def start(self):
        if self._started:
            return
        self._board.setup()
        print(f"[INIT] Starting {self._name} servo on GPIO {self._pin}...")
        self._driver = create_driver(self._pin, self._min_angle, self._max_angle)
        self._driver.start()
        self._started = True

    def set_angle(self, angle: float) -> bool:
        if self._driver is None:
            raise RuntimeError(f"{self._name} servo not started")
        return self._driver.set_angle(angle)

    def stop(self):
        if self._driver is not None:
            self._driver.stop()
            self._driver = None
        self._started = False
