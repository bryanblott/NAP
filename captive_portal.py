import uasyncio as asyncio
from wifi_access_point import WiFiAccessPoint
from dns_server import DNSServer
from http_server import HTTPServer

class CaptivePortal:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678", server_ip="192.168.4.1"):
        self.wifi_ap = WiFiAccessPoint(ssid, password)
        self.dns_server = DNSServer(server_ip)
        self.http_server = HTTPServer()

    async def start(self):
        # Start the Wi-Fi Access Point
        await self.wifi_ap.start()

        # Start DNS and HTTP in background without blocking event loop
        print("Starting DNS and HTTP servers in parallel...")
        await asyncio.gather(
            self.dns_server.run(),  # DNS server in background
            self.http_server.start()  # HTTP server in background
        )

        # Keep the main task running indefinitely
        while True:
            await asyncio.sleep(3600)