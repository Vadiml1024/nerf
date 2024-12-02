from tkinter import NO
import requests
import time


class NerfController:
    def __init__(self, server_url):
        self.server_url = server_url.rstrip("/")  # Remove trailing slash if present

    def fire(self, x=0, y=0, shot=1, wait=True):
        url = f"{self.server_url}/nerf"
        params = {"x": x, "y": y, "shots": shot}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            print("Gun response: ", response.json())
            rr = response.json()
            rm = rr.get("message", "shots:0")
            rm = "{" + rm.strip().replace(" ", ",") + "}"
            rmdict = eval(rm)
            shots = rmdict.get("shots", 0)

            if wait:
                ok, status = self.wait_until_idle(shots=shots)
                return ok, status
            return ok, status
        except Exception as e:
            print("Gun Error: ", e)
            return False, {"status": "error", "message": str(e), "shots": 0}

    def stop(self):
        url = f"{self.server_url}/stop"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def get_status(self):
        url = f"{self.server_url}/status"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def wait_until_idle(self, timeout=30, check_interval=0.5, shots=0):
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if status["status"] == "idle":
                status["shots"] = shots
                return True, status
            elif status["status"] == "ko":
                status["shots"] = 0
                return False, status
            elif status["status"] == "error":
                status["shots"] = 0
                return False, status
            time.sleep(check_interval)
        return False, status


# Example usage
if __name__ == "__main__":
    nerf = NerfController("http://localhost:5555")

    print(nerf.fire(x=10, y=20, shot=3))
    nerf.wait_until_idle()

    print(nerf.get_status())

    print(nerf.stop())
