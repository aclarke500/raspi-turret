import math

diagonal_fov_deg = 55
aspect_w = 16
aspect_h = 9
diag_rad = math.radians(diagonal_fov_deg)
aspect_diag = math.sqrt(aspect_w**2 + aspect_h**2)

# Calculate horizontal and vertical FOVs
hfov = 2 * math.degrees(math.atan(math.tan(diag_rad/2) * (aspect_w / aspect_diag)))
vfov = 2 * math.degrees(math.atan(math.tan(diag_rad/2) * (aspect_h / aspect_diag)))


def x_offset_to_degrees(x_offset):
    return -1*x_offset*hfov/2


def y_offset_to_degrees(y_offset):
    return -1*y_offset*vfov/2