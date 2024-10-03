
################################################################################
# wifi_client.py
#
# WiFiClient is a class that manages the scanning and connection to Wi-Fi
# networks using an ESP32 device. It allows the device to transition from AP
# mode to client mode based on user input from the captive portal.
#
# Attributes:
#     ssid (str): The SSID of the Wi-Fi network to connect to.
#     password (str): The password for the Wi-Fi network.
#     sta (network.WLAN): The network interface for client mode.
#
# Methods:
#     __init__(): Initializes the WiFiClient class with a network interface.
#     scan_networks(): Scans and returns a list of available networks.
#     connect(ssid, password): Connects to the specified Wi-Fi network.
#     get_ip_address(): Retrieves the current IP address of the client.
################################################################################

################################################################################
# Dependencies
################################################################################
import network
import uasyncio as asyncio
from logging_utility import log

################################################################################
# Code
################################################################################
class WiFiClient:
    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)  # Initialize the station interface
        self.ssid = None
        self.password = None

    def scan_networks(self):
        # Scan for available Wi-Fi networks and return a list of SSIDs
        self.sta.active(True)  # Activate the station interface
        networks = self.sta.scan()  # Scan for available networks
        return [net[0].decode("utf-8") for net in networks]  # Return only SSIDs

    async def connect(self, ssid, password):
        # Connect to the specified Wi-Fi network with the provided password
        self.ssid = ssid
        self.password = password
        log(f"Attempting to connect to SSID: {ssid}")
        self.sta.active(True)  # Ensure the station interface is active
        self.sta.connect(ssid, password)  # Start connection attempt

        # Wait until connection is established or timeout after 15 seconds
        for _ in range(15):
            if self.sta.isconnected():
                log(f"Connected to {ssid}. IP address: {self.sta.ifconfig()[0]}")
                return True
            await asyncio.sleep(1)
        
        log(f"Failed to connect to SSID: {ssid}", "ERROR")  # Connection failed
        return False

    def get_ip_address(self):
        # Get the current IP address of the client mode
        if self.sta.isconnected():
            return self.sta.ifconfig()[0]
        return None

    def stop(self):
        # Deactivate the station interface to stop client mode
        self.sta.active(False)
        log("Client mode deactivated.")
