import logging
import requests
from contextlib import ContextDecorator


class ReqLogger(ContextDecorator):
    def __init__(self, level=logging.DEBUG, log_to_console=True, log_file=None):
        self.level = level
        self.log_to_console = log_to_console
        self.log_file = log_file
        self.loggers = [ logging.getLogger(x) for x in ["aiohttp.client", "aiohttp.web"] ]
        self.file_handler = None
        self.stream_handler = None
        self.previous_level = []

    def __enter__(self):
        # Save the previous logging level to restore it after context exits
 
        if self.log_to_console:
            self.stream_handler = logging.StreamHandler()
            self.stream_handler.setLevel(self.level)

        if self.log_file:
            self.file_handler = logging.FileHandler(self.log_file)
            self.file_handler.setLevel(self.level)

        for logger in self.loggers:
            self.previous_level.append(logger.level)
            logger.setLevel(self.level)
            if self.log_to_console:
                # Set up console logging if required
                logger.addHandler(self.stream_handler)
            if self.log_file:
                logger.addHandler(self.file_handler)

 
        # Enable verbose logging of request and response details including headers
        http_logger = logging.getLogger("requests.packages.urllib3")
        http_logger.setLevel(self.level)
        http_logger.propagate = True

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the previous logging level
        for logger,level in zip(self.loggers, self.previous_level):
            logger.setLevel(level)

        # Remove stream handler if added
        if self.stream_handler:
            for logger in self.loggers:
                logger.removeHandler(self.stream_handler)
            self.stream_handler = None

        # Remove file handler if added
        if self.file_handler:
            for logger in self.loggers:
                logger.removeHandler(self.file_handler)

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