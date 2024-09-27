import network
import uasyncio as asyncio

class WiFiAccessPoint:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678"):
        self.ssid = ssid
        self.password = password
        self.ap = network.WLAN(network.AP_IF)

    async def start(self):
        """Start the Wi-Fi access point"""
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password)
        print(f"Access Point {self.ssid} started")

        # Wait until the AP gets an IP address
        while not self.ap.active():
            print("Waiting for AP to become active...")
            await asyncio.sleep(1)

        # Print the AP's IP address configuration
        ap_ip = self.ap.ifconfig()
        print(f"AP IP configuration: {ap_ip}")