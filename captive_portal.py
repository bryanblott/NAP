# captive_portal.py
import uasyncio as asyncio
import machine
from logging_utility import log
from wifi_access_point import WiFiAccessPoint
from dns_server import DNSServer
from http_server import HTTPServer

class CaptivePortal:
    def __init__(self, config):
        self.wifi_ap = WiFiAccessPoint(config["ssid"], config["password"])
        self.dns_server = DNSServer(config["server_ip"])
        self.http_server = HTTPServer()  # Using HTTPServer with optional TLS support
        self.dns_task = None
        self.http_task = None

    async def start(self):
        # Start the Wi-Fi Access Point
        self.wifi_ap.start()

        # Start DNS and HTTP in background without blocking event loop
        log("Starting DNS and HTTP servers in parallel...")
        self.dns_task = asyncio.create_task(self.dns_server.run())  # DNS server in background
        self.http_task = asyncio.create_task(self.http_server.start())  # HTTP/HTTPS server in background

        # Enable watchdog timer to prevent hangs or crashes
        wdt = machine.WDT(timeout=10000)  # 10 seconds watchdog timeout
        log("Watchdog timer enabled.")

        # Keep the main task running indefinitely and feed the watchdog
        try:
            while True:
                wdt.feed()  # Feed the watchdog to prevent reset
                await asyncio.sleep(5)  # Sleep for a while before next feed
        except asyncio.CancelledError:
            log("Main loop task cancelled, stopping services...", "WARNING")

    async def stop(self):
        """Stop all servers and release resources."""
        log("Stopping Captive Portal...")
        # Cancel tasks and ensure they are awaited
        if self.http_task:
            log("Cancelling HTTP server task...")
            self.http_task.cancel()  # Cancel the HTTP/HTTPS task
            try:
                await asyncio.wait_for(self.http_task, timeout=5)
            except asyncio.TimeoutError:
                log("HTTP task timed out during cancellation.", "WARNING")
            except asyncio.CancelledError:
                log("HTTP task was cancelled.", "WARNING")

        if self.dns_task:
            log("Cancelling DNS server task...")
            self.dns_task.cancel()  # Cancel the DNS task
            try:
                await asyncio.wait_for(self.dns_task, timeout=5)
            except asyncio.TimeoutError:
                log("DNS task timed out during cancellation.", "WARNING")
            except asyncio.CancelledError:
                log("DNS task was cancelled.", "WARNING")

        # Close the HTTP server
        await self.http_server.close_server()
        log("Captive Portal stopped.")
