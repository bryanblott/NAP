################################################################################
# Dependencies
################################################################################
import network  # For WiFi Access Point
import socket  # For DNS Server
import uasyncio as asyncio  # For DNS Server, HTTP Server, Captive Portal, Main
import gc  # For HTTP Server

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
        """Start the Wi-Fi access point"""
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password)
        print(f"Access Point {self.ssid} started")

        # Wait until the AP gets an IP address
        while not self.ap.active():
            print("Waiting for AP to become active...")
            await asyncio.sleep(1)

        # Print the AP's IP address configuration
        ap_ip = self.ap.ifconfig()
        print(f"AP IP configuration: {ap_ip}")

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
# Class to build an HTTP Server
################################################################################

class HTTPServer:
    def __init__(self, index_file='index.html'):
        self.index_file = index_file
        self.server = None  # Keep a reference to the server

    async def handle_connection(self, reader, writer):
        gc.collect()
        print("Handling HTTP request")

        # Basic response (no file handling for now)
        response = 'HTTP/1.0 200 OK\r\n\r\n'
        response += "<html><body><h1>ESP32 Captive Portal - Test Response</h1></body></html>"

        await writer.awrite(response)
        await writer.aclose()

    async def start(self):
        """Start the HTTP server on port 80 after a brief delay to ensure the network is ready."""
        await asyncio.sleep(3)  # Wait for Wi-Fi to fully initialize

        if self.server:
            print("Closing existing HTTP server instance before starting a new one.")
            await self.close_server()  # Close existing server before starting a new one

        try:
            print("Attempting to start HTTP server on port 80...")
            self.server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 80)
            print("HTTP server successfully started on port 80.")
        except OSError as e:
            print(f"Error starting HTTP server on port 80: {e}. Trying port 8080...")
            try:
                self.server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 8080)
                print("HTTP server started on port 8080.")
            except OSError as e2:
                print(f"Error starting HTTP server on port 8080: {e2}")
                raise e2

    async def close_server(self):
        """Gracefully close the HTTP server if it exists."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("HTTP server closed successfully.")
            self.server = None

################################################################################
# Putting the whole captive portal together
################################################################################

class CaptivePortal:
    def __init__(self, ssid="ESP32_Captive_Portal", password="12345678", server_ip="192.168.4.1"):
        self.wifi_ap = WiFiAccessPoint(ssid, password)
        self.dns_server = DNSServer(server_ip)
        self.http_server = HTTPServer()

    async def start(self):
        # Start the Wi-Fi Access Point
        await self.wifi_ap.start()

        # Start DNS and HTTP in background without blocking event loop
        print("Starting DNS and HTTP servers in parallel...")
        asyncio.create_task(self.dns_server.run())  # DNS server in background
        asyncio.create_task(self.http_server.start())  # HTTP server in background

        # Keep the main task running indefinitely
        while True:
            await asyncio.sleep(3600)

    async def stop(self):
        """Stop all servers and release resources."""
        print("Stopping Captive Portal...")
        if self.http_server:
            await self.http_server.close_server()
        if self.dns_server and self.dns_server.udps:
            self.dns_server.udps.close()
            print("DNS server stopped.")

################################################################################
# Main Loop
# Running the whole system
################################################################################
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
    if IS_UASYNCIO_V3:
        asyncio.run(portal.stop())  # Ensure all servers are closed
        asyncio.new_event_loop()  # Clear retained state
    else:
        loop.run_until_complete(portal.stop())  # For older asyncio versions
