import network
import uasyncio as asyncio
import time
import utime

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
                return await self.connect(self.config['ssid'], self.config['password'])
            else:
                print(f"[INFO] STA interface SSID not set, initializing without connecting")
                return True
        else:
            print(f"[ERROR] Unknown interface type: {self.type}")
            return False
        
        return self.is_connected()

    async def connect(self, ssid, password):
        if self.type != "sta":
            print("[ERROR] Connect method is only available for STA interface")
            return False

        print(f"[INFO] Attempting to connect to {ssid}")
        self.interface.active(True)
        self.interface.disconnect()
        self.interface.connect(ssid, password)

        start_time = time.time()
        while time.time() - start_time < 30:  # 30 seconds timeout
            await asyncio.sleep(1)
            if self.is_connected():
                print(f"[INFO] Connected to {ssid}. IP: {self.get_ip()}")
                print("[DEBUG] Waiting for 2 seconds to allow post-connection processes to complete")
                utime.sleep(2)  # 2-second delay
                try:
                    print("[DEBUG] Performing post-connection operations")
                    self.interface.config(pm = 0xa11140)  # Disable power-saving mode
                    print("[DEBUG] Power-saving mode disabled")
                    # Add any other post-connection operations here
                    print("[DEBUG] All post-connection operations completed successfully")
                except Exception as e:
                    print(f"[ERROR] Error in post-connection operations: {e}")
                return True
            print(f"[DEBUG] Waiting for connection... Time elapsed: {time.time() - start_time:.1f}s")
            status = self.interface.status()
            print(f"[DEBUG] Connection status: {status}")
            if status == network.STAT_CONNECTING:
                print("[DEBUG] Still connecting...")
            elif status == network.STAT_WRONG_PASSWORD:
                print("[ERROR] Wrong password")
                return False
            elif status == network.STAT_NO_AP_FOUND:
                print("[ERROR] AP not found")
                return False
            elif status == network.STAT_CONNECT_FAIL:
                print("[ERROR] Connection failed")
                return False

        print(f"[ERROR] Failed to connect to {ssid} (Timeout)")
        print(f"[DEBUG] Final connection status: {self.interface.status()}")
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
            self.interface.disconnect()
            self.interface.active(False)
        print(f"[INFO] {self.type.upper()} interface stopped")

    def get_ip(self):
        if self.is_connected():
            return self.interface.ifconfig()[0]
        return None

    async def scan_networks(self):
        print("[DEBUG] Performing network scan")
        if self.type != "sta":
            print("[ERROR] Scan method is only available for STA interface")
            return []
        
        self.interface.active(True)
        try:
            networks = self.interface.scan()
            return [net[0].decode('utf-8') for net in networks]
        except Exception as e:
            print(f"[ERROR] Scan failed: {e}")
            return []

    async def reconnect(self):
        if self.type == "sta" and self.config['ssid']:
            print(f"[INFO] Attempting to reconnect to {self.config['ssid']}")
            return await self.connect(self.config['ssid'], self.config['password'])
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