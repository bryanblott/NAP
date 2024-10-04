
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
from logging_utility import create_logger

# Create a logger for this module
logger = create_logger("WiFiClient")

################################################################################
# Code
################################################################################
class WiFiClient:
    def __init__(self):
        """Initialize the WiFi client interface."""
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    async def connect(self, ssid, password):
        """Connect to a WiFi network."""
        self.wlan.connect(ssid, password)
        for _ in range(10):
            if self.wlan.isconnected():
                logger.info(f"Connected to {ssid} successfully.")
                return True
            await asyncio.sleep(1)
        logger.warning(f"Failed to connect to {ssid}.")
        return False

    async def scan(self):
        """Scan for available WiFi networks."""
        try:
            networks = self.wlan.scan()
            logger.info("Scanned WiFi networks successfully.")
            return networks
        except Exception as e:
            logger.error(f"Failed to scan WiFi networks: {e}")
            return []

    def is_connected(self):
        """Check if the WiFi client is connected to a network."""
        return self.wlan.isconnected()

if __name__ == "__main__":
    # Example usage of the WiFi client
    wifi_client = WiFiClient()
    loop = asyncio.get_event_loop()

    async def test_connection():
        ssid = 'YourSSID'
        password = 'YourPassword'
        connected = await wifi_client.connect(ssid, password)
        if connected:
            logger.info("WiFi connection test passed.")
            networks = await wifi_client.scan()
            logger.info(f"Available networks: {networks}")
        else:
            logger.error("WiFi connection test failed.")
        await wifi_client.disconnect()

    loop.run_until_complete(test_connection())
    loop.close()
    logger.info("WiFi client test completed.")
