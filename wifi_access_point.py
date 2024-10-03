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
from network import WLAN, AP_IF
import uasyncio as asyncio
from logging_utility import get_logger

# Create a logger for this module
logger = get_logger("WiFiAccessPoint")

################################################################################
# Code
################################################################################
class WiFiAccessPoint:
    def __init__(self, ssid, password):
        """Initialize the WiFi access point with given SSID and password."""
        self.ssid = ssid
        self.password = password
        self.wlan = WLAN(AP_IF)
        self.wlan.active(True)
        self.wlan.config(essid=self.ssid, password=self.password, authmode=3)

    def start(self):
        """Start the WiFi Access Point."""
        try:
            if not self.wlan.active():
                self.wlan.active(True)
            self.wlan.config(essid=self.ssid, password=self.password, authmode=3)
            logger.info("WiFi Access Point started successfully.")
        except Exception as e:
            logger.error(f"Failed to start WiFi Access Point: {e}")

    def stop(self):
        """Stop the WiFi Access Point."""
        try:
            self.wlan.active(False)
            logger.info("WiFi Access Point stopped successfully.")
        except Exception as e:
            logger.error(f"Failed to stop WiFi Access Point: {e}")

    async def monitor(self):
        """Monitor the status of the WiFi Access Point."""
        try:
            while True:
                if self.wlan.active():
                    logger.info("WiFi Access Point is active.")
                else:
                    logger.warning("WiFi Access Point is not active.")
                await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            logger.warning("WiFi Access Point monitoring task was cancelled.")
        except Exception as e:
            logger.error(f"Error during WiFi Access Point monitoring: {e}")

if __name__ == "__main__":
    # Create an instance with example credentials
    ap = WiFiAccessPoint("ExampleSSID", "securepassword123")
    ap.start()
    
    # Start monitoring in an event loop for demonstration purposes
    loop = asyncio.get_event_loop()
    loop.create_task(ap.monitor())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Manual interruption received.")
        ap.stop()
    finally:
        loop.close()
        logger.info("WiFi Access Point process exited gracefully.")
