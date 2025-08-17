import math

def get_fovs(diagonal_fov_deg, aspect_w=16, aspect_h=9):
    diag_rad = math.radians(diagonal_fov_deg)
    aspect_diag = math.sqrt(aspect_w**2 + aspect_h**2)

    # Calculate horizontal and vertical FOVs
    hfov = 2 * math.degrees(math.atan(math.tan(diag_rad/2) * (aspect_w / aspect_diag)))
    vfov = 2 * math.degrees(math.atan(math.tan(diag_rad/2) * (aspect_h / aspect_diag)))
    return hfov, vfov

hfov, vfov = get_fovs(55)
print(f"Horizontal FOV: hfov={hfov}, vfov={vfov}")
