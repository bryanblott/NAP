################################################################################
# Configuration class for managing application settings.
#
# Attributes:
#     CONFIG_FILE (str): The name of the configuration file.
#
# Methods:
#     __init__():
#         Initializes the Configuration object with default settings.
#     
#     save_default_config():
#         Creates and saves the default configuration file if it does not exist.
#     
#     load():
#         Loads configuration from file, or uses defaults if not found.
################################################################################


################################################################################
# Dependencies
################################################################################
import json
import os
from logging_utility import get_logger

# Create a logger for this module
logger = get_logger("Configuration")


################################################################################
# Code
################################################################################
class Configuration:
    CONFIG_FILE = 'config.json'

    def __init__(self, filename=None):
        """Initialize Configuration with a file or default name."""
        # Use provided filename or default
        self.filename = filename if filename else self.CONFIG_FILE
        self.config = {
            'ssid': 'ESP32-Captive-Portal',
            'password': '12345678',
            'server_ip': '192.168.4.1'
        }
        self.load()

    def load(self):
        """Load configuration from the configuration file."""
        try:
            with open(self.filename, 'r') as file:
                self.config = json.load(file)
            logger.info("Configuration loaded successfully.")
        except OSError as e:
            if e.args[0] == 2:  # ENOENT error, file not found
                logger.warning(f"Configuration file '{self.filename}' not found, using default values and creating it.")
                self.save_default_config()
            else:
                logger.error(f"Failed to load configuration file: {e}")
        except json.JSONDecodeError:
            logger.error("Error decoding JSON configuration file. Using default configuration.")
            self.config = self.default_config()
            self.save()
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            self.config = self.default_config()
            self.save()

    def save(self):
        """Save the current configuration to a file."""
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.config, file)
            logger.info(f"Configuration saved successfully to {self.filename}.")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def save_default_config(self):
        """Save the default configuration to the configuration file."""
        self.config = self.default_config()
        self.save()

    def default_config(self):
        """Return the default configuration."""
        return {
            'ssid': 'ESP32-AP',
            'password': '12345678',
            'server_ip': '192.168.4.1'
        }

    def get(self, key):
        """Get a configuration value by key."""
        return self.config.get(key, None)

    def set(self, key, value):
        """Set a configuration value."""
        self.config[key] = value
        self.save()

    def update(self, new_config):
        """Update multiple configuration values at once."""
        self.config.update(new_config)
        self.save()
        logger.info(f"Configuration updated with values: {new_config}")

    def reset_to_defaults(self):
        """Reset configuration to default values."""
        logger.info("Resetting configuration to default values.")
        self.config = self.default_config()
        self.save()

    def display(self):
        """Display the current configuration values."""
        logger.info(f"Current Configuration: {self.config}")

if __name__ == "__main__":
    config = Configuration()
    config.display()  # Display current configuration values







