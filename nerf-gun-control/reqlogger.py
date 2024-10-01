import logging
import requests
from contextlib import ContextDecorator

class ReqLogger(ContextDecorator):
    def __init__(self, level=logging.DEBUG, log_to_console=True, log_file=None):
        self.level = level
        self.log_to_console = log_to_console
        self.log_file = log_file
        self.logger = logging.getLogger("urllib3")
        self.file_handler = None
        self.stream_handler = None
        self.previous_level = None

    def __enter__(self):
        # Save the previous logging level to restore it after context exits
        self.previous_level = self.logger.level

        # Set logging level to the specified level
        self.logger.setLevel(self.level)

        # Set up console logging if required
        if self.log_to_console:
            self.stream_handler = logging.StreamHandler()
            self.stream_handler.setLevel(self.level)
            self.logger.addHandler(self.stream_handler)

        # Set up file logging if a file path is provided
        if self.log_file:
            self.file_handler = logging.FileHandler(self.log_file)
            self.file_handler.setLevel(self.level)
            self.logger.addHandler(self.file_handler)

        # Enable verbose logging of request and response details including headers
        http_logger = logging.getLogger("requests.packages.urllib3")
        http_logger.setLevel(self.level)
        http_logger.propagate = True

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the previous logging level
        self.logger.setLevel(self.previous_level)

        # Remove stream handler if added
        if self.stream_handler:
            self.logger.removeHandler(self.stream_handler)
            self.stream_handler = None

        # Remove file handler if added
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler = None

        return False  # Allows exceptions to propagate

# Example Usage:
if __name__ == "__main__":
    # Using the ReqLogger to log HTTP requests and headers at DEBUG level to the console
    with ReqLogger(level=logging.DEBUG):
        response = requests.get('https://httpbin.org/get', headers={'Custom-Header': 'HeaderValue'})
        print(response.status_code)

    # Using the ReqLogger to log HTTP requests and headers at INFO level to a file
    with ReqLogger(level=logging.INFO, log_to_console=False, log_file='http_requests_with_headers.log'):
        response = requests.get('https://httpbin.org/status/200', headers={'Another-Header': 'AnotherValue'})
        print(response.status_code)