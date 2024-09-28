# configuration.py
import json
from logging_utility import log

class Configuration:
    CONFIG_FILE = 'config.json'

    def __init__(self):
        # Default configuration
        self.config = {"ssid": "ESP32_Captive_Portal", "password": "12345678", "server_ip": "192.168.4.1"}

    def save_default_config(self):
        """Create and save the default configuration file if it does not exist."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
            log("Default configuration created and saved as 'config.json'.")
        except Exception as e:
            log(f"Failed to create default configuration: {e}", "ERROR")

    def load(self):
        """Load configuration from file, or use defaults if not found."""
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
            log("Configuration loaded successfully.")
        except OSError as e:
            if e.args[0] == 2:  # ENOENT error, file not found
                log("Configuration file not found, using default values and creating it.", "WARNING")
                self.save_default_config()
            else:
                log(f"Failed to load configuration: {e}", "ERROR")
        except Exception as e:
            log(f"Failed to load configuration: {e}", "ERROR")
