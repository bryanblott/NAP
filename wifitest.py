################################################################################
# Dependencies
################################################################################
import network
import socket
import uasyncio as asyncio
import gc
import time
from microdot import Microdot, Response, redirect

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)

################################################################################
# Class to build a WiFi Access Point with more detailed logging and error handling
################################################################################

class WiFiAccessPoint:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678"):
        self.ssid = ssid
        self.password = password
        self.ap = network.WLAN(network.AP_IF)

    def start(self):
        """Start the Wi-Fi access point with detailed error handling and more status checks."""
        try:
            print(f"Configuring Access Point with SSID: {self.ssid} and Password: {self.password}")
            self.ap.active(True)
            self.ap.config(essid=self.ssid, password=self.password)

            print(f"Access Point {self.ssid} configuration initiated.")

            # Wait and check for AP status
            for _ in range(10):
                status = self.ap.status()
                print(f"Current Wi-Fi Status: {status}")
                if self.ap.active() and status == network.STAT_GOT_IP:
                    break
                print("Waiting for AP to become active...")
                time.sleep(1)  # Use time.sleep to wait and check status

            # Check final status
            if not self.ap.active():
                raise RuntimeError(f"Failed to activate the Access Point. Status: {self.ap.status()}")

            ap_ip = self.ap.ifconfig()
            print(f"Access Point {self.ssid} started successfully. AP IP configuration: {ap_ip}")

        except Exception as e:
            print(f"An error occurred while starting the Access Point: {e}")
            raise e

################################################################################
# Test Wi-Fi Initialization Without Other Services
################################################################################

try:
    # Create a simple Wi-Fi Access Point instance to verify connectivity
    wifi_ap_test = WiFiAccessPoint()
    wifi_ap_test.start()  # Start Wi-Fi AP without any additional services

    # Wait for a few seconds to confirm stability
    print("Wi-Fi AP is running without other services. Confirm stability...")
    time.sleep(10)

    print("Wi-Fi AP test completed successfully. No DNS or HTTP services are running.")

except Exception as e:
    print(f"An exception occurred during Wi-Fi AP test: {e}")


# Add this to the existing Wi-Fi AP test code
# dns_server_test = DNSServer()
# asyncio.run(dns_server_test.run())  # Run DNS server with uasyncio