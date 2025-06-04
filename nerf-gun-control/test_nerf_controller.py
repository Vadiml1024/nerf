import os
import sys
import pytest
from unittest.mock import patch, Mock

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from nerf_controller import NerfController

@pytest.fixture
def nerf_controller():
    return NerfController("http://test-server.com")

@patch('nerf_controller.NerfController.wait_until_idle')
@patch('nerf_controller.requests.get')
def test_fire_success(mock_get, mock_wait, nerf_controller):
    mock_response = Mock()
    mock_response.json.return_value = {"message": "shots:3"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    mock_wait.return_value = (True, {"status": "idle", "shots": 3})

    success, data = nerf_controller.fire(x=10, y=20, shot=3)

    assert success is True
    assert data == {"status": "idle", "shots": 3}
    mock_get.assert_called_once_with("http://test-server.com/nerf", params={'x': 10, 'y': 20, 'shot': 3})
    mock_wait.assert_called_once_with(shots=3)

@patch('nerf_controller.requests.get')
def test_fire_error(mock_get, nerf_controller):
    mock_get.side_effect = Exception("Connection error")

    success, data = nerf_controller.fire(x=10, y=20, shot=3)
    assert success is False
    assert data == {"status": "error", "message": "Connection error", "shots": 0}

@patch('nerf_controller.requests.get')
def test_stop_success(mock_get, nerf_controller):
    mock_response = Mock()
    mock_response.text = "Nerf stopped"
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = nerf_controller.stop()
    assert result == "Nerf stopped"
    mock_get.assert_called_once_with("http://test-server.com/stop")

@patch('nerf_controller.requests.get')
def test_get_status_success(mock_get, nerf_controller):
    mock_response = Mock()
    mock_response.json.return_value = {"status": "idle"}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = nerf_controller.get_status()
    assert result == {"status": "idle"}
    mock_get.assert_called_once_with("http://test-server.com/status")

@patch('nerf_controller.requests.get')
def test_get_status_error(mock_get, nerf_controller):
    mock_get.side_effect = Exception("Connection error")

    result = nerf_controller.get_status()
    assert result == {"status": "error", "message": "Connection error"}

@patch('nerf_controller.NerfController.get_status')
def test_wait_until_idle_success(mock_get_status, nerf_controller):
    mock_get_status.side_effect = [
        {"status": "busy"},
        {"status": "busy"},
        {"status": "idle"}
    ]

    success, status = nerf_controller.wait_until_idle(timeout=5, check_interval=0.1)
    assert success is True
    assert status["status"] == "idle"
    assert mock_get_status.call_count == 3

@patch('nerf_controller.NerfController.get_status')
def test_wait_until_idle_timeout(mock_get_status, nerf_controller):
    mock_get_status.return_value = {"status": "busy"}

    success, status = nerf_controller.wait_until_idle(timeout=0.5, check_interval=0.1)
    assert success is False
    assert status["status"] == "busy"
    assert mock_get_status.call_count > 1

if __name__ == "__main__":
    pytest.main([__file__])
    