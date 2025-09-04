#!/usr/bin/env python
# filepath: /Users/vadim/work/nerf/init-obs-messages.py
import os
from datetime import datetime
from nerf_gun_control.params import OBS_MESSAGE_LOG_FILE

def initialize_obs_log():
    """Initialize the OBS message log file with a welcome message."""
    try:
        # Create the log file directory if it doesn't exist
        os.makedirs(os.path.dirname(OBS_MESSAGE_LOG_FILE), exist_ok=True)
        
        # Create or clear the log file and write initial messages
        with open(OBS_MESSAGE_LOG_FILE, 'w') as f:
            timestamp = datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] System: Nerf Gun Status Display Initialized\n")
            f.write(f"[{timestamp}] System: Gun status: INACTIVE\n")
        
        print(f"OBS message log file initialized at: {OBS_MESSAGE_LOG_FILE}")
        return True
    except Exception as e:
        print(f"Error initializing OBS log file: {e}")
        return False

if __name__ == "__main__":
    initialize_obs_log()