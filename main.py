import uasyncio as asyncio
from dns_server import DNSServer
from http_server import HTTPServer
from wifi_manager import WiFiManager
from configuration import Configuration

class CaptivePortal:
    def __init__(self):
        print("[DEBUG] Initializing CaptivePortal...")
        self.config = Configuration()  # Load the configuration
        print("[INFO] CaptivePortal: Configuration loaded successfully.")
        self.dns_server = DNSServer()
        print("[INFO] CaptivePortal: DNSServer initialized.")
        self.http_server = HTTPServer(cert_file='cert.pem', key_file='private.key', root_directory='www', host='0.0.0.0', port=80)
        print("[INFO] CaptivePortal: HTTPServer initialized.")
        self.wifi_manager = WiFiManager(self.config)
        print("[INFO] CaptivePortal: WiFiManager initialized.")

    async def start(self):
        try:
            print("[DEBUG] CaptivePortal: Starting start() method")
            
            # AP is already started in WiFiManager initialization
            print(f"[INFO] CaptivePortal: Access Point active with SSID: {self.config.get_ssid()}")

            # Run DNS and HTTP servers as concurrent tasks
            try:
                print("[INFO] CaptivePortal: Starting DNS server.")
                dns_task = asyncio.create_task(self.dns_server.start())
                print("[DEBUG] CaptivePortal: DNS server task created successfully.")

                print("[INFO] CaptivePortal: Starting HTTP server.")
                http_task = asyncio.create_task(self.http_server.start())
                print("[DEBUG] CaptivePortal: HTTP server task created successfully.")

                print("[INFO] CaptivePortal: Services started successfully.")
                await asyncio.gather(dns_task, http_task)
            except Exception as e:
                print(f"[ERROR] CaptivePortal: Exception in starting servers: {type(e).__name__}: {str(e)}")

        except Exception as e:
            print(f"[ERROR] CaptivePortal: Exception occurred in start() method: {type(e).__name__}: {str(e)}")
        finally:
            # Ensure all services are stopped cleanly
            print("[INFO] CaptivePortal: Initiating shutdown.")
            await self.shutdown()

    async def shutdown(self):
        print("[INFO] CaptivePortal: Shutting down services.")
        try:
            print("[DEBUG] CaptivePortal: Stopping DNS server.")
            await self.dns_server.stop()
            print("[INFO] CaptivePortal: DNS server stopped.")
        except Exception as e:
            print(f"[ERROR] CaptivePortal: Error stopping DNS server: {type(e).__name__}: {str(e)}")

        try:
            print("[DEBUG] CaptivePortal: Stopping HTTP server.")
            await self.http_server.stop()
            print("[INFO] CaptivePortal: HTTP server stopped.")
        except Exception as e:
            print(f"[ERROR] CaptivePortal: Error stopping HTTP server: {type(e).__name__}: {str(e)}")

        try:
            print("[DEBUG] CaptivePortal: Stopping WiFi Access Point.")
            self.wifi_manager.stop_ap()
            print("[INFO] CaptivePortal: WiFi Access Point stopped.")
        except Exception as e:
            print(f"[ERROR] CaptivePortal: Error stopping WiFi Access Point: {type(e).__name__}: {str(e)}")

        print("[INFO] CaptivePortal: All services stopped.")

async def main():
    captive_portal = CaptivePortal()
    try:
        print("[INFO] Main: Starting Captive Portal.")
        await captive_portal.start()
    except KeyboardInterrupt:
        print("[INFO] CaptivePortal: Keyboard interrupt received, shutting down.")
    except Exception as e:
        print(f"[ERROR] Main: Unexpected exception: {type(e).__name__}: {str(e)}")
    finally:
        # Ensure shutdown is completed properly in case of an exception
        print("[DEBUG] Main: Ensuring proper shutdown.")
        await captive_portal.shutdown()

if __name__ == "__main__":
    asyncio.run(main())