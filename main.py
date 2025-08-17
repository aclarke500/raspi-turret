from Turret import Turret
import signal, sys


T = Turret()  # Create an instance
T.setup()

def handle_exit(sig, frame):
    turret.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

while True:
    # x_offset_degrees, y_offset_degrees = T.patrol()
    # if x_offset_degrees is not None:
    #     T.snap_to_target(x_offset_degrees, y_offset_degrees)
    time.sleep(2)
    T.traverse()
    
