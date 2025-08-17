from Turret import Turret
from utils.utils import x_offset_to_degrees
import signal, sys
import time

T = Turret()  # Create an instance
T.setup()

def handle_exit(sig, frame):
    T.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

while True:
    x_offset_of_target, y_offset_of_target = T.patrol()
    if x_offset_of_target is not None:
        # Convert normalized offsets to degrees
        x_offset_degrees = x_offset_to_degrees(x_offset_of_target)
        y_offset_degrees = x_offset_to_degrees(y_offset_of_target)  # Using same conversion for Y
        T.snap_to_target(x_offset_degrees, y_offset_degrees)
    # time.sleep(2)
    # T.patrol()
    
