################################################################################
# This module provides a simple Logger class with methods like `info`, `error`,
# and `warning` to print messages with different severity levels.
################################################################################

print("Initializing logging_utility.py")  # Add this line at the top

class Logger:
    """Simple Logger class to encapsulate logging functionality."""
    
    def __init__(self, name=None):
        self.name = name

    def _log(self, message, level="INFO"):
        """Log a message with a specific severity level."""
        print(f"[{level}] {message}")

    def info(self, message):
        self._log(message, "INFO")

    def warning(self, message):
        self._log(message, "WARNING")

    def error(self, message):
        self._log(message, "ERROR")

def get_logger(name=None):
    """Return an instance of the Logger class."""
    return Logger(name)
