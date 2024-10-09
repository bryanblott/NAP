import json
import os

class Configuration:
    CONFIG_FILE = 'config.json'

    def __init__(self, filename=None):
        """Initialize Configuration with a file or default name."""
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
                config_data = json.load(file)
                self.config.update(config_data)
            print("[INFO] Configuration loaded successfully.")
        except OSError as e:
            if e.args[0] == 2:  # ENOENT error, file not found
                print(f"[WARNING] Configuration file '{self.filename}' not found, using default values and creating it.")
                self.save_default_config()
            else:
                print(f"[ERROR] Failed to load configuration file: {e}")
        except json.JSONDecodeError:
            print("[ERROR] Error decoding JSON configuration file. Using default configuration.")
            self.config = self.default_config()
            self.save()
        except Exception as e:
            print(f"[ERROR] Unexpected error loading configuration: {e}")
            self.config = self.default_config()
            self.save()

    def save(self):
        """Save the current configuration to a file."""
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.config, file)
            print(f"[INFO] Configuration saved successfully to {self.filename}.")
        except Exception as e:
            print(f"[ERROR] Failed to save configuration: {e}")

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

    # Add getter methods below
    def get_ssid(self):
        """Get the SSID value from the configuration."""
        return self.config.get('ssid', 'ESP32-Captive-Portal')

    def get_password(self):
        """Get the Wi-Fi password from the configuration."""
        return self.config.get('password', '12345678')

    # Remaining methods
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
        print(f"[INFO] Configuration updated with values: {new_config}")

    def reset_to_defaults(self):
        """Reset configuration to default values."""
        print("[INFO] Resetting configuration to default values.")
        self.config = self.default_config()
        self.save()

    def display(self):
        """Display the current configuration values."""
        print(f"[INFO] Current Configuration: {self.config}")

if __name__ == "__main__":
    config = Configuration()
    config.display()  # Display current configuration values