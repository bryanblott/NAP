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
from wifi_access_point import WiFiAccessPoint
from dns_server import DNSServer
from http_server import HTTPServer
from logging_utility import get_logger

# Create a logger for this module
logger = get_logger("CaptivePortal")


################################################################################
# Captive Portal Class Definition
################################################################################
class CaptivePortal:
    def __init__(self, config):
        """Initialize the CaptivePortal with the given configuration."""
        self.config = config
        self.wifi_ap = WiFiAccessPoint(self.config['ssid'], self.config['password'])
        self.dns_server = DNSServer(self.config['server_ip'])
        self.http_server = HTTPServer(self.config['server_ip'], 80)
    
    async def start(self):
        """Start the captive portal services: Wi-Fi AP, DNS server, and HTTP server."""
        try:
            logger.info("Starting Captive Portal...")
            self.wifi_ap.start()
            await asyncio.gather(
                self.dns_server.start(),
                self.http_server.start()
            )
            logger.info("Captive Portal started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Captive Portal services: {e}")
    
    async def stop(self):
        """Stop the captive portal services."""
        try:
            logger.info("Stopping Captive Portal...")
            await asyncio.gather(
                self.wifi_ap.stop(),
                self.dns_server.stop(),
                self.http_server.stop()
            )
            logger.info("Captive Portal stopped successfully.")
        except Exception as e:
            logger.error(f"Failed to stop Captive Portal services: {e}")
    
    async def run_forever(self):
        """Keep the captive portal running indefinitely."""
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
        except asyncio.CancelledError:
            logger.warning("Captive Portal run_forever task was cancelled.")
            await self.stop()

if __name__ == "__main__":
    # Example configuration dictionary
    config = {
        'ssid': 'ESP32-Captive-Portal',
        'password': '123456789',
        'server_ip': '192.168.4.1'
    }
    
    cp = CaptivePortal(config)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(cp.start())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Manual interruption received.")
    finally:
        loop.run_until_complete(cp.stop())
        loop.close()
        logger.info("Captive Portal process exited gracefully.")
