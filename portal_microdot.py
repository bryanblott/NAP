################################################################################
# Dependencies
################################################################################
import network  # For WiFi Access Point
import socket  # For DNS Server
import select  # For DNS Server
import uasyncio as asyncio  # For DNS Server
import gc  # For Garbage Collection
from microdot import Microdot, send_file

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

    def start(self):
        """Start the Wi-Fi access point"""
        try:
            self.ap.active(False)  # Disable Wi-Fi before starting to ensure a clean start
            self.ap.active(True)
            self.ap.config(essid=self.ssid, password=self.password)
            print(f"Access Point {self.ssid} started")

            # Print the AP's IP address configuration
            ap_ip = self.ap.ifconfig()
            print(f"AP IP configuration: {ap_ip}")

        except OSError as e:
            print(f"Error starting Wi-Fi access point: {e}")

        except Exception as e:
            print(f"Unexpected error: {e}")

    def stop(self):
        """Stop the Wi-Fi access point"""
        self.ap.active(False)
        print(f"Access Point {self.ssid} stopped")

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

    async def run(self):
        """Run the DNS server to handle incoming DNS requests"""
        udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udps.setblocking(False)  # Set the socket to non-blocking mode
        udps.bind(('0.0.0.0', 53))

        print("DNS server started on port 53")

        while True:
            try:
                # Use non-blocking socket to wait for incoming data
                data, addr = await asyncio.get_event_loop().sock_recvfrom(udps, 4096)
                print("Incoming DNS request...")

                DNS = DNSQuery(data)
                print(f"Received DNS query for domain: {DNS.domain}")
                udps.sendto(DNS.response(self.server_ip), addr)

                print(f"Replying: {DNS.domain} -> {self.server_ip}")

            except Exception as e:
                print(f"Error handling DNS query: {e}")
                await asyncio.sleep(3)

        udps.close()


################################################################################
# Class to build an HTTP Server with Microdot
################################################################################

class HTTPServer:
    def __init__(self):
        self.app = Microdot()

        # Define a route to handle root requests
        @self.app.route('/')
        async def index(request):
            return 'ESP32 Captive Portal - Microdot Test'

        # Define additional routes as needed
        @self.app.route('/redirect')
        async def redirect(request):
            return 'HTTP/1.1 302 Found\r\nLocation: http://192.168.4.1/\r\n\r\n'

    async def start(self):
        """Start the HTTP server on port 80"""
        await asyncio.sleep(3)  # Wait for Wi-Fi to fully initialize
        try:
            print("Attempting to start Microdot HTTP server on port 80...")
            await self.app.start_server(host='0.0.0.0', port=80)
            print("Microdot HTTP server successfully started on port 80.")
        except OSError as e:
            print(f"Error starting Microdot HTTP server on port 80: {e}")
            raise

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
        self.wifi_ap.start()

        # Start the DNS server as a background task
        print("Starting DNS server...")
        asyncio.create_task(self.dns_server.run())

        # Start the Microdot HTTP server
        print("Starting Microdot HTTP server...")
        await self.http_server.start()

        # Keep the main task running indefinitely
        while True:
            await asyncio.sleep(3600)

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
    print('Bye')

finally:
    if IS_UASYNCIO_V3:
        asyncio.new_event_loop()  # Clear retained state
