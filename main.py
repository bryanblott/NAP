import uasyncio as asyncio
from dns_server import DNSServer
from http_server import HTTPServer
from wifi_manager import WiFiManager
from configuration import Configuration

class CaptivePortal:
    def __init__(self):
        self.config = Configuration()
        self.http_server = HTTPServer(
            root_directory='www', 
            host='0.0.0.0', 
            port=80, 
            ssl_certfile='cert.pem', 
            ssl_keyfile='private.key'
        )
        self.wifi_manager = WiFiManager(self.config, self.http_server)
        self.dns_server = DNSServer()
        self.http_server.set_wifi_manager(self.wifi_manager)  # Set the WiFiManager
        self.stop_event = asyncio.Event()

    async def start(self):
        print(f"[INFO] CaptivePortal: Starting AP with SSID: {self.config.get_ssid()}")
        self.wifi_manager.start_ap(self.config.get_ssid(), self.config.get_password())

        dns_task = asyncio.create_task(self.dns_server.start())
        http_task = asyncio.create_task(self.http_server.start())

        print("[INFO] CaptivePortal: Services started successfully.")
        await self.stop_event.wait()

        # Cancel tasks
        dns_task.cancel()
        http_task.cancel()
        await asyncio.gather(dns_task, http_task, return_exceptions=True)

    async def shutdown(self):
        print("[INFO] CaptivePortal: Initiating shutdown...")
        self.stop_event.set()
        await asyncio.sleep(1)

        self.wifi_manager.stop_ap()
        print("[INFO] CaptivePortal: Shutdown complete")

async def main():
    captive_portal = CaptivePortal()
    try:
        await captive_portal.start()
    except asyncio.CancelledError:
        pass
    finally:
        await captive_portal.shutdown()

def run():
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("[INFO] Main: Keyboard interrupt received, shutting down...")
    finally:
        main_task.cancel()
        loop.run_until_complete(main_task)
        loop.close()
        print("[INFO] Main: Cleanup complete. Exiting program.")

if __name__ == "__main__":
    run()