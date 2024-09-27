################################################################################
# Dependencies
################################################################################
import logging  # Library for logging
import network  # For WiFi Access Point
import socket  # For DNS Server
import select  # For DNS Server
import uasyncio as asyncio  # For DNS Server
import gc  # For Garbage Collection
from microdot import Microdot, send_file

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)

# Configure logging
logging.basicConfig(level=logging.INFO)

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
            logging.info(f"Access Point {self.ssid} started")

            # Log the AP's IP address configuration
            ap_ip = self.ap.ifconfig()
            logging.info(f"AP IP configuration: {ap_ip}")

        except OSError as e:
            logging.error(f"Error starting Wi-Fi access point: {e}")

        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    def stop(self):
        """Stop the Wi-Fi access point"""
        self.ap.active(False)
        logging.info(f"Access Point {self.ssid} stopped")

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

        logging.info("DNS server started on port 53")

        while True:
            try:
                # Use non-blocking socket to wait for incoming data
                data, addr = await asyncio.get_event_loop().sock_recvfrom(udps, 4096)
                logging.info("Incoming DNS request...")

                DNS = DNSQuery(data)
                logging.info(f"Received DNS query for domain: {DNS.domain}")
                udps.sendto(DNS.response(self.server_ip), addr)

                logging.info(f"Replying: {DNS.domain} -> {self.server_ip}")

            except Exception as e:
                logging.error(f"Error handling DNS query: {e}")
                await asyncio.sleep(3)

        udps.close()

################################################################################
# Class to build an HTTP Server with Microdot
################################################################################

class HTTPServer:
    def __init__(self):
        self.app = Microdot()

        @self.app.route('/')
        def index(request):
            return send_file('index.html')

    def start(self):
        """Start the HTTP server"""
        try:
            self.app.run(host='0.0.0.0', port=80)
            logging.info("HTTP server started on port 80")
        except Exception as e:
            logging.error(f"Error starting HTTP server: {e}")

################################################################################
# Class to build a Captive Portal
################################################################################

class CaptivePortal:
    def __init__(self):
        self.wifi_ap = WiFiAccessPoint()
        self.dns_server = DNSServer()
        self.http_server = HTTPServer()

    async def start(self):
        """Start the captive portal"""
        self.wifi_ap.start()
        asyncio.create_task(self.dns_server.run())
        self.http_server.start()

        while True:
            await asyncio.sleep(1)

################################################################################
# Main Loop
################################################################################

if __name__ == "__main__":
    try:
        captive_portal = CaptivePortal()
        asyncio.run(captive_portal.start())
    except KeyboardInterrupt:
        logging.info("Captive portal stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")