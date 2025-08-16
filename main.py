from Turret import Turret
T = Turret()  # Create an instance
T.setup()

while True:
    offset = T.patrol()
    
