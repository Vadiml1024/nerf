import pytest
import time
from nerf_gun_control.nerf_controller import NerfController

# Make sure this URL matches your Nerf server address
SERVER_URL = "http://localhost:5555"

@pytest.fixture(scope="module")
def nerf_controller():
    return NerfController(SERVER_URL)

def test_fire_and_wait(nerf_controller):
    # Fire 3 shots
    response = nerf_controller.fire(x=10, y=20, shot=3)
    print(f"Fire response: {response}")
    assert "Nerf activated" in response

    # Wait for Nerf to become idle
    assert nerf_controller.wait_until_idle(timeout=5), "Nerf did not return to idle state within the timeout period"

    # Check status after waiting
    status = nerf_controller.get_status()
    print(f"Status after wait: {status}")
    assert status['status'] == 'idle', f"Expected status was 'idle', but got {status['status']}"

def test_stop(nerf_controller):
    # Stop the Nerf
    response = nerf_controller.stop()
    print(f"Stop response: {response}")
    assert "Nerf stopped" in response

    # Check status after stopping
    status = nerf_controller.get_status()
    print(f"Status after stop: {status}")
    assert status['status'] == 'idle', f"Expected status was 'idle', but got {status['status']}"

def test_multiple_fires(nerf_controller):
    for i in range(3):
        print(f"Firing round {i+1}")
        response = nerf_controller.fire(x=i*10, y=i*5, shot=i+1)
        print(f"Fire response: {response}")
        assert "Nerf activated" in response

        # Wait for Nerf to become idle before next fire
        assert nerf_controller.wait_until_idle(timeout=5), f"Nerf did not return to idle state after fire {i+1}"

        status = nerf_controller.get_status()
        print(f"Status after fire {i+1}: {status}")
        assert status['status'] == 'idle', f"Expected status was 'idle', but got {status['status']}"

        # Short pause between fires
        time.sleep(1)

def test_busy_state(nerf_controller):
    # Fire with many shots to ensure Nerf is busy
    response = nerf_controller.fire(x=0, y=0, shot=10)
    print(f"Fire response: {response}")
    assert "Nerf activated" in response

    # Immediately check status, should be "busy"
    status = nerf_controller.get_status()
    print(f"Immediate status after fire: {status}")
    assert status['status'] == 'busy', f"Expected status was 'busy', but got {status['status']}"

    # Try to fire again while Nerf is busy
    busy_response = nerf_controller.fire(x=10, y=10, shot=1)
    print(f"Busy fire response: {busy_response}")
    assert "Error" in busy_response, "Fire request during busy state should have failed"

    # Wait for Nerf to become idle again
    assert nerf_controller.wait_until_idle(timeout=10), "Nerf did not return to idle state within the timeout period"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])