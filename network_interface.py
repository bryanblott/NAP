import network
import uasyncio as asyncio

class NetworkInterface:
    def __init__(self, interface_type, config):
        self.type = interface_type
        self.config = config
        self.interface = None

    async def start(self):
        print(f"Starting {self.type} interface...")
        if self.type == "ap":
            self.interface = network.WLAN(network.AP_IF)
            self.interface.active(True)
            self.interface.config(essid=self.config['ssid'], password=self.config['password'])
        elif self.type == "sta":
            self.interface = network.WLAN(network.STA_IF)
            self.interface.active(True)
            if self.config['ssid']:
                self.interface.connect(self.config['ssid'], self.config['password'])
            else:
                print(f"[INFO] STA interface SSID not set, initializing without connecting")
                return True
        else:
            print(f"[ERROR] Unknown interface type: {self.type}")
            return False
        
        for _ in range(20):  # Wait up to 20 seconds for connection
            if self.is_connected():
                print(f"{self.type.upper()} Interface connected. IP: {self.interface.ifconfig()[0]}")
                return True
            await asyncio.sleep(1)
        
        print(f"Failed to connect {self.type} interface")
        return False

    async def connect(self, ssid, password):
        if self.type != "sta":
            print("[ERROR] Connect method is only available for STA interface")
            return False

        print(f"[INFO] Attempting to connect to {ssid}")
        self.interface.disconnect()
        self.interface.connect(ssid, password)
        
        for _ in range(20):  # Wait up to 20 seconds for connection
            if self.is_connected():
                print(f"[INFO] Connected to {ssid}. IP: {self.get_ip()}")
                return True
            await asyncio.sleep(1)
        
        print(f"[ERROR] Failed to connect to {ssid}")
        return False

    def is_connected(self):
        if self.interface is None:
            return False
        if self.type == "ap":
            return self.interface.active()
        elif self.type == "sta":
            return self.interface.isconnected()
        return False

    async def stop(self):
        if self.interface:
            self.interface.active(False)
        print(f"{self.type.upper()} interface stopped")

    def get_ip(self):
        if self.is_connected():
            return self.interface.ifconfig()[0]
        return None

    async def scan_networks(self):
        if self.type == "sta" and self.interface:
            try:
                print("[DEBUG] Starting network scan...")
                self.interface.active(True)
                networks = self.interface.scan()
                print(f"[DEBUG] Scan complete. Found {len(networks)} networks.")
                unique_ssids = list(set([net[0].decode('utf-8') for net in networks]))
                print(f"[DEBUG] Unique SSIDs: {unique_ssids}")
                return unique_ssids
            except Exception as e:
                print(f"[ERROR] Failed to scan networks: {e}")
                return []
        else:
            print("[ERROR] Cannot scan networks on non-STA interface")
            return []

    async def reconnect(self):
        if self.type == "sta" and self.config['ssid']:
            print(f"[INFO] Attempting to reconnect to {self.config['ssid']}")
            self.interface.disconnect()
            self.interface.connect(self.config['ssid'], self.config['password'])
            for _ in range(20):  # Wait up to 20 seconds for connection
                if self.is_connected():
                    print(f"STA Interface reconnected. IP: {self.interface.ifconfig()[0]}")
                    return True
                await asyncio.sleep(1)
            print("Failed to reconnect STA interface")
            return False
        else:
            print("[ERROR] Reconnect not applicable for this interface type")
            return False

    def get_status(self):
        if self.interface is None:
            return "Not initialized"
        if self.is_connected():
            return f"Connected (IP: {self.get_ip()})"
        return "Disconnected"

    def get_config(self):
        return {
            "type": self.type,
            "ssid": self.config.get('ssid', ''),
            "is_connected": self.is_connected(),
            "ip": self.get_ip()
        }