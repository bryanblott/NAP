################################################################################
# wifi_access_point.py
#
# WiFiAccessPoint is a class that manages the creation and control of a Wi-Fi 
# access point using an ESP32 device.
#
# Attributes:
#     ssid (str): The SSID (name) of the Wi-Fi access point.
#     password (str): The password for the Wi-Fi access point.
#     ap (network.WLAN): The network interface for the access point.
#
# Methods:
#     __init__(ssid="ESP32_Captive_Portal", password="12345678"):
#         Initializes the WiFiAccessPoint with the given SSID and password.
#     start():
#         Starts the Wi-Fi access point and waits until it becomes active. 
#         Logs the IP configuration once active.
################################################################################


################################################################################
# Dependencies
################################################################################
import network 
import time
from logging_utility import log


################################################################################
# Code
################################################################################
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
