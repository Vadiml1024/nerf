from tkinter import NO
import requests
import time
import json


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
            rml = rm.split("shots:")
            shots = int(rml[1]) if len(rml) > 1 else -1

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
            print("Getting status")
            response = requests.get(url)
            response.raise_for_status()
            print("Status: ", response.json())
            return response.json()
        except Exception as e:
            print("Error getting status: ", e)
            return {"status": "error", "message": str(e)}

    def wait_until_idle(self, timeout=45, check_interval=0.1, shots=0):
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if status["status"] == "idle":
                if not ("shots" in status):
                    status["shots"] = shots
                return True, status
            elif status["status"] == "ko":
                if not ("shots" in status):
                    status["shots"] = 0
                return False, status
            elif status["status"] == "error":
                if not ("shots" in status):
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
