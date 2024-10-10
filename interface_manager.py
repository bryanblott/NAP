import uasyncio as asyncio
from network_interface import NetworkInterface


class InterfaceManager:
    def __init__(self, config):
        self.config = config
        self.interfaces = {}

    async def start_interface(self, interface_type):
        if interface_type not in self.interfaces:
            if interface_type == 'ap':
                interface_config = self.config.get_ap_config()
            elif interface_type == 'sta':
                interface_config = self.config.get_sta_config()
                if not interface_config.get('ssid'):
                    print(f"[INFO] STA SSID not set, initializing STA interface without connecting")
                    interface_config['ssid'] = ''
                    interface_config['password'] = ''
            else:
                print(f"[ERROR] Unknown interface type: {interface_type}")
                return False

            try:
                interface = NetworkInterface(interface_type, interface_config)
                if await interface.start():
                    self.interfaces[interface_type] = interface
                    print(f"[INFO] {interface_type.upper()} interface started successfully")
                    return True
                else:
                    print(f"[ERROR] Failed to start {interface_type.upper()} interface")
            except Exception as e:
                print(f"[ERROR] Exception while starting {interface_type.upper()} interface: {e}")
        return False

    async def stop_interface(self, interface_type):
        if interface_type in self.interfaces:
            try:
                await self.interfaces[interface_type].stop()
                del self.interfaces[interface_type]
                print(f"[INFO] {interface_type.upper()} interface stopped")
            except Exception as e:
                print(f"[ERROR] Exception while stopping {interface_type.upper()} interface: {e}")
            return True
        return False

    async def stop_all_interfaces(self):
        for interface_type in list(self.interfaces.keys()):
            await self.stop_interface(interface_type)
        print("[INFO] All interfaces stopped")

    async def manage_interfaces(self):
        while True:
            for interface_type in list(self.interfaces.keys()):
                interface = self.interfaces[interface_type]
                if not interface.is_connected():
                    print(f"[WARNING] {interface_type.upper()} disconnected. Attempting to reconnect...")
                    await self.stop_interface(interface_type)
                    await self.start_interface(interface_type)
            await asyncio.sleep(10)  # Check every 10 seconds

    def get_active_interfaces(self):
        return [itype for itype, interface in self.interfaces.items() if interface.is_connected()]