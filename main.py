from Turret import Turret
T = Turret()  # Create an instance
T.setup()

while True:
    x_offset_degrees, y_offset_degrees = T.patrol()
    if x_offset_degrees is not None:
        T.snap_to_target(x_offset_degrees, y_offset_degrees)
    
