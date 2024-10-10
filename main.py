import uasyncio as asyncio
from dns_server import DNSServer
from http_server import HTTPServer
from interface_manager import InterfaceManager
from configuration import Configuration
import machine

class CaptivePortal:
    def __init__(self):
        self.config = Configuration()
        self.interface_manager = InterfaceManager(self.config)
        self.http_server = HTTPServer(
            root_directory='www', 
            host='0.0.0.0', 
            port=80, 
            ssl_certfile='cert.pem', 
            ssl_keyfile='private.key'
        )
        self.http_server.set_interface_manager(self.interface_manager)
        self.dns_server = DNSServer()
        self.stop_event = asyncio.Event()

    async def start(self):
        print("[INFO] CaptivePortal: Starting interfaces")
        ap_started = await self.interface_manager.start_interface("ap")
        sta_started = await self.interface_manager.start_interface("sta")

        if not ap_started and not sta_started:
            print("[ERROR] Failed to start any interface. Shutting down.")
            return

        dns_task = asyncio.create_task(self.dns_server.start())
        http_task = asyncio.create_task(self.http_server.start())
        interface_management_task = asyncio.create_task(self.interface_manager.manage_interfaces())

        print("[INFO] CaptivePortal: Services started successfully.")
        await self.stop_event.wait()

        # Cancel tasks
        dns_task.cancel()
        http_task.cancel()
        interface_management_task.cancel()
        await asyncio.gather(dns_task, http_task, interface_management_task, return_exceptions=True)

    async def shutdown(self):
        print("[INFO] CaptivePortal: Initiating shutdown...")
        self.stop_event.set()
        await asyncio.sleep(1)

        await self.interface_manager.stop_all_interfaces()
        await self.http_server.stop()
        print("[INFO] CaptivePortal: Shutdown complete")

    async def reset_device(self):
        print("[INFO] Resetting the device...")
        await asyncio.sleep(1)  # Give some time for the message to be printed
        machine.reset()

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