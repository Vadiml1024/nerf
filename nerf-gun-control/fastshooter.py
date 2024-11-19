from nerf_controller import NerfController
from params import NERF_CONTROLLER_URL

nerf = NerfController(NERF_CONTROLLER_URL)

# Generate random coordinates pairs
import random
import time

coords = [(random.randint(-45, 45), random.randint(0, 60)) for _ in range(100)]

for x, y in coords:
    print(f"Firing at x={x}, y={y}")
    nerf.fire(x, y, 0)
    #time.sleep(1)
    ok, status = nerf.wait_until_idle()
    if not ok:
        print(f"Error: {status}")
        break
    # time.sleep(1)
