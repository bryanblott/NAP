import machine # type: ignore
import uasyncio as asyncio # type: ignore
from utils import log_with_timestamp  # Updated import
from dns_server import DNSServer
from http_server import HTTPServer
from interface_manager import InterfaceManager
from configuration import Configuration
import utime

class CaptivePortal:
    def __init__(self):
        self.config = Configuration()
        self.interface_manager = InterfaceManager(self.config)
        self.http_server = HTTPServer(self.interface_manager)
        # Set HTTP server properties after initialization
        self.http_server.root_directory = 'www'
        self.http_server.ports = [80]
        self.http_server.ssl_ports = [443]
        self.http_server.ssl_certfile = 'cert.pem'
        self.http_server.ssl_keyfile = 'private.key'
        self.server_ip = self.config.get_server_ip()
        self.dns_server = DNSServer(self.server_ip)
        self.stop_event = asyncio.Event()

    async def reset_sta_interface(self):
        log_with_timestamp("[INFO] Resetting STA interface")
        await self.interface_manager.stop_interface('sta')
        await asyncio.sleep(1)
        await self.interface_manager.start_interface('sta')

    async def start(self):
        log_with_timestamp("[INFO] CaptivePortal: Starting interfaces")
        await asyncio.sleep(2)  # Add a small delay before starting services
        ap_started = await self.interface_manager.start_interface("ap")
        sta_started = await self.interface_manager.start_interface("sta")

        if not ap_started and not sta_started:
            print("[ERROR] Failed to start any interface. Shutting down.")
            return

        dns_task = asyncio.create_task(self.dns_server.start())
        http_task = asyncio.create_task(self.http_server.start())
        interface_management_task = asyncio.create_task(self.manage_interfaces())
        
        print("[INFO] CaptivePortal: Services started successfully.")
        
        try:
            await asyncio.gather(dns_task, http_task, interface_management_task)
        except asyncio.CancelledError:
            print("[INFO] CaptivePortal: Shutting down...")
        finally:
            await self.shutdown()

    async def shutdown(self):
        print("[INFO] CaptivePortal: Initiating shutdown...")
        await self.interface_manager.stop_all_interfaces()
        await self.http_server.stop()
        print("[INFO] CaptivePortal: Shutdown complete")

    async def reset_device(self):
        print("[INFO] Resetting the device...")
        await asyncio.sleep(1)  # Give some time for the message to be printed
        machine.reset()

    async def manage_interfaces(self):
        while True:
            await asyncio.sleep(60)  # Check every 60 seconds
            sta_interface = self.interface_manager.get_interface('sta')
            if sta_interface:
                if not sta_interface.is_connected() and not sta_interface.is_connecting():
                    log_with_timestamp("[WARNING] STA disconnected. Attempting to reset and reconnect...")
                    await self.reset_sta_interface()
            else:
                log_with_timestamp("[WARNING] STA interface not available. Attempting to start it...")
                await self.interface_manager.start_interface('sta')

async def main():
    captive_portal = CaptivePortal()
    try:
        await captive_portal.start()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[ERROR] Unexpected error in main: {e}")
    finally:
        await captive_portal.shutdown()
        await captive_portal.reset_device()

def run():
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("[INFO] Main: Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"[ERROR] Unexpected error in run: {e}")
    finally:
        main_task.cancel()
        try:
            loop.run_until_complete(main_task)
        except asyncio.CancelledError:
            pass
        loop.close()
        print("[INFO] Main: Cleanup complete. Resetting device...")
        machine.reset()  # Reset the device after cleanup

if __name__ == "__main__":
    run()
