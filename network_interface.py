import network
import uasyncio as asyncio
import time
import utime
from utils import log_with_timestamp  # Updated import

class NetworkInterface:
    def __init__(self, interface_type, config):
        self.type = interface_type
        self.config = config
        self.interface = None
        self.connecting = False  # Add this line

    async def start(self):
        log_with_timestamp(f"Starting {self.type} interface...")
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
                log_with_timestamp(f"[INFO] STA interface SSID not set, initializing without connecting")
                return True
        else:
            log_with_timestamp(f"[ERROR] Unknown interface type: {self.type}")
            return False
        
        return True

    async def connect(self, ssid, password):
        log_with_timestamp(f"[INFO] Attempting to connect to '{ssid}'")
        self.connecting = True  # Set the flag
        try:
            self.interface.connect(ssid, password)
            start_time = utime.time()
            while not self.interface.isconnected():
                if utime.time() - start_time > 30:  # 30 second timeout
                    log_with_timestamp(f"[ERROR] Failed to connect to '{ssid}' after 30 seconds")
                    log_with_timestamp(f"[DEBUG] Connection status: {self.interface.status()}")
                    self.connecting = False  # Reset the flag
                    return False
                log_with_timestamp(f"[DEBUG] Waiting for connection... Time elapsed: {utime.time() - start_time}s")
                log_with_timestamp(f"[DEBUG] Connection status: {self.interface.status()}")
                await asyncio.sleep(1)
            
            log_with_timestamp(f"[INFO] Connected to '{ssid}'. IP: {self.get_ip()}")
            self.connecting = False  # Reset the flag
            return True
        except Exception as e:
            log_with_timestamp(f"[ERROR] Exception while connecting to '{ssid}': {e}")
            self.connecting = False  # Reset the flag
            return False

    def is_connected(self):
        return self.interface and self.interface.isconnected()

    def get_ip(self):
        if self.is_connected():
            return self.interface.ifconfig()[0]
        return None

    async def scan_networks(self):
        log_with_timestamp("[DEBUG] Performing network scan")
        if self.type != "sta":
            log_with_timestamp("[ERROR] Scan method is only available for STA interface")
            return []
        
        self.interface.active(True)
        try:
            networks = self.interface.scan()
            log_with_timestamp(f"[DEBUG] Scan result: {networks}")
            return [net[0].decode('utf-8') for net in networks if net[0]]  # Only return non-empty SSIDs
        except Exception as e:
            log_with_timestamp(f"[ERROR] Scan failed: {e}")
            return []

    async def reconnect(self):
        if self.type == "sta" and self.config['ssid']:
            log_with_timestamp(f"[INFO] Attempting to reconnect to {self.config['ssid']}")
            return await self.connect(self.config['ssid'], self.config['password'])
        else:
            log_with_timestamp("[ERROR] Reconnect not applicable for this interface type")
            return False

    async def stop(self):
        log_with_timestamp(f"Stopping {self.type} interface...")
        if self.interface:
            self.interface.active(False)
            self.interface = None
        log_with_timestamp(f"[INFO] {self.type.upper()} interface stopped")

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

    # Add this method
    def is_connecting(self):
        return self.connecting
