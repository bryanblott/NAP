################################################################################
# Dependencies
################################################################################
import network  # For WiFi Access Point
import socket  # For DNS Server
import uasyncio as asyncio  # For DNS Server, HTTP Server, Captive Portal, Main
import gc  # For HTTP Server
from microdot import Microdot

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)

################################################################################
# Class to build a WiFi Access Point
################################################################################

class WiFiAccessPoint:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678"):
        self.ssid = ssid
        self.password = password
        self.ap = network.WLAN(network.AP_IF)

    async def start(self):
        """Start the Wi-Fi access point with detailed debug information."""
        try:
            print("Deactivating any existing Wi-Fi Access Point...")
            self.ap.active(False)  # Reset AP before starting
            await asyncio.sleep(1)  # Small delay to ensure reset

            print("Activating Wi-Fi Access Point...")
            self.ap.active(True)
            print(f"Setting AP configuration with SSID: {self.ssid}")
            self.ap.config(essid=self.ssid, password=self.password)
            print(f"Access Point {self.ssid} started successfully.")
        except Exception as e:
            print(f"Failed to start Access Point: {e}")
            raise

        # Wait until the AP gets an IP address
        retry_count = 0
        while not self.ap.active():
            print(f"Waiting for AP to become active... (Attempt {retry_count})")
            retry_count += 1
            await asyncio.sleep(1)
            if retry_count > 10:  # Timeout after 10 attempts (10 seconds)
                raise Exception("AP activation timed out")

        ap_ip = self.ap.ifconfig()
        print(f"AP IP configuration: {ap_ip}")

    def is_active(self):
        """Check if the Wi-Fi AP is active and has an IP address."""
        return self.ap.active()

################################################################################
# DNSQuery Class to Handle DNS Requests
################################################################################

class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        self.parse_domain()

    def parse_domain(self):
        """Parse the domain name from the DNS query"""
        state = 0
        expected_length = 0
        domain_parts = []
        for byte in self.data[12:]:
            if state == 1:
                if byte == 0:
                    break
                domain_parts.append(chr(byte))
                expected_length -= 1
                if expected_length == 0:
                    domain_parts.append('.')
                    state = 0
            else:
                expected_length = byte
                if expected_length == 0:
                    break
                state = 1
        self.domain = ''.join(domain_parts).strip('.')

    def response(self, ip):
        """Generate a response for the given IP address"""
        packet = self.data[:2] + b'\x81\x80'
        packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'  # Questions and Answers Counts
        packet += self.data[12:]  # Original Domain Name Question
        packet += b'\xc0\x0c'  # Pointer to domain name
        packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'  # Response type, ttl and resource data length -> 4 bytes
        packet += bytes(map(int, ip.split('.')))  # 4 bytes of IP

        return packet

################################################################################
# Class to build a DNS Server
################################################################################

class DNSServer:
    def __init__(self, server_ip="192.168.4.1"):
        self.server_ip = server_ip
        self.udps = None

    async def run(self):
        """Run the DNS server to handle incoming DNS requests"""
        print("Starting DNS server...")
        try:
            self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udps.setblocking(False)  # Set the socket to non-blocking mode
            self.udps.bind(('0.0.0.0', 53))

            print("DNS server started on port 53")

            while True:
                try:
                    await self.handle_dns(self.udps)
                except Exception as e:
                    print(f"Error handling DNS query: {e}")
                    await asyncio.sleep(1)
        except OSError as e:
            print(f"Failed to bind DNS server on port 53: {e}")
            raise e  # Re-raise exception if the server fails to start
        finally:
            if self.udps:
                self.udps.close()

    async def handle_dns(self, sock):
        """Handle DNS requests with a polling approach"""
        try:
            # Try receiving data from the socket, non-blocking
            data, addr = sock.recvfrom(4096)
            DNS = DNSQuery(data)
            print(f"Received DNS query for domain: {DNS.domain}")
            sock.sendto(DNS.response(self.server_ip), addr)
            print(f"Replying: {DNS.domain} -> {self.server_ip}")
        except OSError as e:
            if e.args[0] == 11:  # EAGAIN or no data received yet
                await asyncio.sleep(0)  # Yield control back to the event loop
            else:
                print(f"Unexpected error in DNS handling: {e}")
                raise

################################################################################
# Class to build an HTTP Server using Microdot
################################################################################

class HTTPServer:
    async def start(self):
        """Start the Microdot HTTP server."""
        print("Initializing Microdot HTTP server...")
        app = Microdot()

        @app.route('/')
        async def index(request):
            return 'Hello, world!'

        print("Starting HTTP server on port 80...")
        self.server_task = asyncio.create_task(app.start_server(host="0.0.0.0", port=80))
        print("HTTP server started.")

    async def stop(self):
        """Stop the Microdot HTTP server."""
        if hasattr(self, 'server_task') and self.server_task:
            print("Stopping HTTP server...")
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                print("HTTP server task cancelled.")

################################################################################
# Putting the whole captive portal together
################################################################################

class CaptivePortal:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678", server_ip="192.168.4.1"):
        self.wifi_ap = WiFiAccessPoint(ssid, password)
        self.dns_server = DNSServer(server_ip)
        self.http_server = HTTPServer()

    async def start(self):
        # Start the Wi-Fi Access Point and verify
        print("Starting Wi-Fi AP and checking status...")
        await self.wifi_ap.start()

        if not self.wifi_ap.is_active():
            raise Exception("Wi-Fi AP failed to become active. Aborting.")

        print("Wi-Fi AP is active, waiting to ensure stability...")
        await asyncio.sleep(5)  # Additional delay to avoid race conditions

        # Start DNS and HTTP in background without blocking event loop
        print("Starting DNS server...")
        dns_task = asyncio.create_task(self.dns_server.run())  # DNS server in background
        await asyncio.sleep(0)  # Yield control to ensure DNS server has started

        print("Starting HTTP server...")
        http_task = asyncio.create_task(self.http_server.start())  # HTTP server in background
        await asyncio.sleep(0)  # Yield control to ensure HTTP server has started

        # Keep the main task running indefinitely
        try:
            print("Captive Portal is running. Keeping main task alive...")
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            print("Main loop cancelled, stopping services...")

    async def stop(self):
        """Stop all servers and release resources."""
        print("Stopping Captive Portal...")
        if self.http_server:
            await self.http_server.stop()
        if self.dns_server and self.dns_server.udps:
            self.dns_server.udps.close()
            print("DNS server stopped.")

################################################################################
# Main Loop
# Running the whole system
################################################################################
portal = None  # Define portal variable at the top of the try block
try:
    # Instantiate Portal and run
    portal = CaptivePortal()

    print("Starting event loop...")
    if IS_UASYNCIO_V3:
        asyncio.run(portal.start())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(portal.start())

except Exception as e:
    print(f'An exception occurred: {e}')

except KeyboardInterrupt:
    print('Keyboard Interrupt detected. Shutting down...')

finally:
    if portal:  # Check if portal was successfully instantiated
        if IS_UASYNCIO_V3:
            asyncio.run(portal.stop())  # Ensure all servers are closed
            asyncio.new_event_loop()  # Clear retained state
        else:
            loop.run_until_complete(portal.stop())  # For older asyncio versions
