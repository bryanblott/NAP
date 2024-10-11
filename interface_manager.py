import uasyncio as asyncio
from network_interface import NetworkInterface
import time

class InterfaceManager:
    def __init__(self, config):
        self.config = config
        self.interfaces = {}
        self.sta_configured = False
        self.last_sta_config_attempt = 0
        self.auto_reconnect_enabled = True

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
                    if interface_type == 'sta':
                        await self.configure_sta_ip()
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
                if interface_type == 'sta':
                    self.sta_configured = False
                return True
            except Exception as e:
                print(f"[ERROR] Exception while stopping {interface_type.upper()} interface: {e}")
        return False

    async def configure_sta_ip(self):
        current_time = time.time()
        if current_time - self.last_sta_config_attempt < 30:
            print("[INFO] Skipping STA IP configuration (too soon since last attempt)")
            return

        self.last_sta_config_attempt = current_time
        sta_interface = self.interfaces.get('sta')
        if sta_interface and sta_interface.is_connected():
            ip_config = self.config.get_sta_ip_config()
            if ip_config.get('static_ip'):
                try:
                    sta_interface.interface.ifconfig((
                        ip_config['static_ip'],
                        ip_config['subnet_mask'],
                        ip_config['gateway'],
                        ip_config['dns_server']
                    ))
                    print(f"[INFO] Configured static IP for STA: {ip_config['static_ip']}")
                    self.sta_configured = True
                except Exception as e:
                    print(f"[ERROR] Failed to set static IP: {e}")
            else:
                print("[INFO] Using DHCP for STA interface")
                self.sta_configured = True

    def disable_auto_reconnect(self):
        self.auto_reconnect_enabled = False

    def enable_auto_reconnect(self):
        self.auto_reconnect_enabled = True

    async def manage_interfaces(self):
        while True:
            if self.auto_reconnect_enabled:
                for interface_type in list(self.interfaces.keys()):
                    interface = self.interfaces[interface_type]
                    if not interface.is_connected():
                        print(f"[WARNING] {interface_type.upper()} disconnected. Attempting to reconnect...")
                        await self.stop_interface(interface_type)
                        await self.start_interface(interface_type)
                    elif interface_type == 'sta' and not self.sta_configured:
                        await self.configure_sta_ip()
            await asyncio.sleep(60)  # Check every 60 seconds

    async def stop_all_interfaces(self):
        for interface_type in list(self.interfaces.keys()):
            await self.stop_interface(interface_type)
        print("[INFO] All interfaces stopped")

    def get_active_interfaces(self):
        return [itype for itype, interface in self.interfaces.items() if interface.is_connected()]

    def get_interface(self, interface_type):
        return self.interfaces.get(interface_type)