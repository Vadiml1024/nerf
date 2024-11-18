import requests
import time

class NerfController:
    def __init__(self, server_url):
        self.server_url = server_url.rstrip('/')  # Remove trailing slash if present

    def fire(self, x=0, y=0, shot=1):
        url = f"{self.server_url}/nerf"
        params = {'x': x, 'y': y, 'shots': shot}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            print("Gun response: ", response.text)
            return response.text
        except Exception as e:
            print("Gun Error: ", e)
            return f"Error: {str(e)}"

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

    def wait_until_idle(self, timeout=30, check_interval=0.5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if status['status'] == 'idle':
                return True
            elif status['status'] == 'error':
                return False
            time.sleep(check_interval)
        return False

# Example usage
if __name__ == "__main__":
    nerf = NerfController("http://localhost:5555")
    
    print(nerf.fire(x=10, y=20, shot=3))
    nerf.wait_until_idle()
    
    print(nerf.get_status())
    
    print(nerf.stop())