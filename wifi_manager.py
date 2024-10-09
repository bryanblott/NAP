import network
import uasyncio as asyncio

class WiFiManager:
    def __init__(self, config):
        self.config = config
        self.ap = network.WLAN(network.AP_IF)
        self.sta = network.WLAN(network.STA_IF)
        
        # Initialize AP mode with configuration
        self.start_ap(self.config.get_ssid(), self.config.get_password())
        
        # Configure STA mode (inactive initially)
        self.sta.active(True)
    
    def start_ap(self, ssid, password):
            """Activate AP mode with provided SSID and password."""
            self.ap.active(True)
            self.ap.config(essid=ssid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)
            print(f"[INFO] WiFiManager: Access Point started with SSID '{ssid}'")
    
    def stop_ap(self):
        """Deactivate AP mode."""
        if self.ap.active():
            self.ap.active(False)
            print("[INFO] WiFiManager: Access Point deactivated.")
    
    async def connect_sta(self, ssid, password):
        """Connect to a WiFi network using STA mode."""
        print(f"[DEBUG] WiFiManager: Attempting to connect to {ssid}")
        self.sta.connect(ssid, password)
        for _ in range(10):  # Wait for up to 10 seconds
            if self.sta.isconnected():
                print(f"[INFO] WiFiManager: Connected to {ssid} successfully.")
                return True
            await asyncio.sleep(1)
        print(f"[WARNING] WiFiManager: Failed to connect to {ssid}.")
        return False

    async def scan_networks(self):
        """Scan for available WiFi networks."""
        networks = []
        try:
            self.sta.active(True)
            networks = self.sta.scan()
            print("[INFO] WiFiManager: Scanned WiFi networks successfully.")
        except Exception as e:
            print(f"[ERROR] WiFiManager: Failed to scan WiFi networks: {e}")
        return networks

    def is_sta_connected(self):
        """Check if STA is connected to a network."""
        return self.sta.isconnected()