def x_offset_to_degrees(x_offset):
    # fov is 55 degrees, since x is signed 
    # we multiply by 27.5 and that tells us our offset
    return -1*x_offset*27.5