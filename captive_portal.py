################################################################################
# This module defines the CaptivePortal class, which is responsible for setting 
# up and managing a captive portal. A captive portal is a web page that users 
# are automatically redirected to when they connect to a Wi-Fi network. This 
# implementation includes starting and stopping Wi-Fi access points, DNS servers, 
# and HTTP servers, with support for asynchronous operations and a watchdog timer 
# to ensure reliability.
#
# Classes:
#     CaptivePortal: Manages the lifecycle of the captive portal, including 
#     starting and stopping the Wi-Fi AP, DNS, and HTTP servers.
#
# Methods:
#     __init__(self, config): Initializes the CaptivePortal with the given 
#     configuration.
#     start(self): Asynchronously starts the Wi-Fi AP, DNS server, and HTTP 
#     server, and keeps the main task running indefinitely.
#     stop(self): Asynchronously stops the DNS and HTTP servers and releases 
#     resources.
################################################################################


################################################################################
# Dependencies
################################################################################
import uasyncio as asyncio
from logging_utility import log
from http_server import HTTPServer
from dns_server import DNSServer
from wifi_access_point import WiFiAccessPoint


################################################################################
# Captive Portal Class Definition
################################################################################
class CaptivePortal:
    def __init__(self, config):
        self.wifi_ap = WiFiAccessPoint(config["ssid"], config["password"])
        self.dns_server = DNSServer(config["server_ip"])
        self.http_server = HTTPServer()
        self.dns_task = None
        self.http_task = None

    async def start(self):
        """Start the captive portal with DNS and HTTP services."""
        log("Starting Captive Portal...")
        # Start Wi-Fi Access Point
        self.wifi_ap.start()

        # Start DNS and HTTP servers
        log("Starting DNS and HTTP servers in parallel...")
        self.dns_task = asyncio.create_task(self.dns_server.start())
        self.http_task = asyncio.create_task(self.http_server.start())

        # Enable the watchdog timer
        # log("Watchdog timer enabled.")

        try:
            while True:
                await asyncio.sleep(5)  # Main loop to keep running
        except asyncio.CancelledError:
            log("Captive Portal main task cancelled.")

    async def stop(self):
        """Stop all services and cancel tasks."""
        log("Stopping Captive Portal...")

        # Cancel HTTP server task
        if self.http_task:
            log("Cancelling HTTP server task...")
            self.http_task.cancel()
            try:
                await self.http_task
                log("HTTP server task was cancelled gracefully.")
            except asyncio.CancelledError:
                log("HTTP server task was cancelled.")

        # Cancel DNS server task
        if self.dns_task:
            log("Cancelling DNS server task...")
            self.dns_task.cancel()
            try:
                await self.dns_task
                log("DNS server task was cancelled gracefully.")
            except asyncio.CancelledError:
                log("DNS server task was cancelled.")

        # Close HTTP and DNS servers
        await self.http_server.close_server()
        await self.dns_server.stop()

        log("Captive Portal stopped.")