
################################################################################
# This module provides a basic Logger class for logging messages in MicroPython.
# Methods like `info`, `error`, and `warning` are provided to print messages
# with different severity levels.
################################################################################

import sys

class Logger:
    """Simple Logger class to encapsulate logging functionality."""
    def __init__(self, name=None):
        self.name = name

    def _log(self, message, level="INFO"):
        """Log a message with a specific severity level."""
        print("[{}] {}: {}".format(level, self.name if self.name else '', message), file=sys.stderr)

    def info(self, message):
        self._log(message, "INFO")

    def warning(self, message):
        self._log(message, "WARNING")

    def error(self, message):
        self._log(message, "ERROR")

# Function to create a new logger instance
def create_logger(name=None):
    return Logger(name)
