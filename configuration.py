import json
import os

class Configuration:
    CONFIG_FILE = 'config.json'

    def __init__(self, filename=None):
        self.filename = filename if filename else self.CONFIG_FILE
        self.config = {
            'ap': {
                'ssid': 'ESP32-Captive-Portal',
                'password': '12345678'
            },
            'sta': {
                'ssid': '',
                'password': ''
            },
            'server_ip': '192.168.4.1',
            'certfile': 'cert.pem',
            'keyfile': 'key.pem'
        }
        self.load()

    def load(self):
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
            self.save()
        except Exception as e:
            print(f"[ERROR] Unexpected error loading configuration: {e}")
            self.save()

    def save(self):
        try:
            with open(self.filename, 'w') as file:
                json.dump(self.config, file)
            print(f"[INFO] Configuration saved successfully to {self.filename}.")
        except Exception as e:
            print(f"[ERROR] Failed to save configuration: {e}")

    def save_default_config(self):
        self.save()

    def get_ap_config(self):
        return self.config['ap']

    def get_sta_config(self):
        return self.config['sta']

    def get_server_ip(self):
        return self.config.get('server_ip', '192.168.4.1')

    def get_cert_file(self):
        return self.config.get('certfile', 'cert.pem')

    def get_key_file(self):
        return self.config.get('keyfile', 'key.pem')

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def update(self, new_config):
        self.config.update(new_config)
        self.save()

    def reset_to_defaults(self):
        self.config = {
            'ap': {
                'ssid': 'ESP32-Captive-Portal',
                'password': '12345678'
            },
            'sta': {
                'ssid': '',
                'password': ''
            },
            'server_ip': '192.168.4.1',
            'certfile': 'cert.pem',
            'keyfile': 'key.pem'
        }
        self.save()

    def display(self):
        print(f"[INFO] Current Configuration: {self.config}")