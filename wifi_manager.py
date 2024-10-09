import network
import uasyncio as asyncio

class WiFiManager:
    def __init__(self, config, http_server):
        self.config = config
        self.http_server = http_server
        self.ap = network.WLAN(network.AP_IF)
        self.sta = network.WLAN(network.STA_IF)
        
        # Configure AP mode
        self.ap.active(True)
        self.ap.config(essid=self.config.get_ssid(), password=self.config.get_password())
        print(f"[INFO] WiFiManager: Access Point configured with SSID '{self.config.get_ssid()}'")

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
        for _ in range(20):  # Increase timeout to 20 seconds
            if self.sta.isconnected():
                print(f"[INFO] WiFiManager: Connected to {ssid} successfully.")
                return True
            await asyncio.sleep(1)
            print(f"[DEBUG] WiFiManager: Connection attempt {_ + 1}/20")
        print(f"[WARNING] WiFiManager: Failed to connect to {ssid}.")
        return False

    async def scan_networks(self):
        """Scan for available WiFi networks."""
        print("[DEBUG] WiFiManager: Scanning for networks")
        self.sta.active(True)
        try:
            networks = self.sta.scan()
            ssids = list(set([net[0].decode('utf-8') for net in networks]))  # Remove duplicates
            print(f"[INFO] WiFiManager: Found {len(ssids)} unique networks")
            return ssids
        except Exception as e:
            print(f"[ERROR] WiFiManager: Error scanning networks: {e}")
            return []

    def is_sta_connected(self):
        """Check if STA is connected to a network."""
        return self.sta.isconnected()

    def get_sta_ip(self):
        """Get the IP address of the STA interface."""
        if self.sta.isconnected():
            return self.sta.ifconfig()[0]
        return None

    async def connect_to_network(self, ssid, password):
        """Connect to a specific network."""
        print(f"[INFO] WiFiManager: Attempting to connect to network: {ssid}")
        self.sta.active(True)
        self.sta.connect(ssid, password)
        
        # Wait for connection with timeout
        for _ in range(20):  # 20 second timeout
            if self.sta.isconnected():
                break
            await asyncio.sleep(1)
        
        if self.sta.isconnected():
            ip_address = self.sta.ifconfig()[0]
            print(f"[INFO] WiFiManager: Connected to {ssid}. IP address: {ip_address}")
            
            # Restart HTTP server
            await asyncio.sleep(2)  # Give some time for network to stabilize
            await self.http_server.restart()
            
            return True
        else:
            print(f"[WARNING] WiFiManager: Failed to connect to {ssid}")
            return False

    def get_current_ssid(self):
        """Get the SSID of the currently connected network."""
        if self.sta.isconnected():
            return self.sta.config('essid')
        return None

    async def reconnect(self):
        """Attempt to reconnect to the last known network."""
        ssid = self.get_current_ssid()
        if ssid:
            password = self.config.get_password()  # Assuming you store the password in the config
            return await self.connect_to_network(ssid, password)
        return False