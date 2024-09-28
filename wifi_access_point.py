# wifi_access_point.py
import network # type: ignore
import time
from logging_utility import log

class WiFiAccessPoint:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678"):
        self.ssid = ssid
        self.password = password
        self.ap = network.WLAN(network.AP_IF)

    def start(self):
        """Start the Wi-Fi access point"""
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password)
        log(f"Access Point {self.ssid} started")

        # Wait until the AP gets an IP address
        while not self.ap.active():
            log("Waiting for AP to become active...", "WARNING")
            time.sleep(1)

        # Print the AP's IP address configuration
        ap_ip = self.ap.ifconfig()
        log(f"AP IP configuration: {ap_ip}")
