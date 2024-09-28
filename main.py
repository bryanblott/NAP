################################################################################
# Dependencies
################################################################################
import network  # For WiFi Access Point
import socket  # For DNS Server
import uasyncio as asyncio  # For DNS Server, HTTP Server, Captive Portal, Main
import gc  # For HTTP Server
import time  # For non-blocking sleep in Wi-Fi Access Point class
import machine  # For Watchdog Timer
import sys  # For system exit
import json  # For configuration file handling
import os  # For checking if certificate and key files exist
import tls  # For SSL/TLS support in MicroPython 1.23.0 and later

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)


################################################################################
# Logging Utility
################################################################################
def log(message, level="INFO"):
    """Simple logging utility to print messages with a severity level."""
    print(f"[{level}] {message}")


################################################################################
# Configuration Management
################################################################################
class Configuration:
    CONFIG_FILE = 'config.json'

    def __init__(self):
        # Default configuration
        self.config = {"ssid": "ESP32_Captive_Portal", "password": "12345678", "server_ip": "192.168.4.1"}

    def save_default_config(self):
        """Create and save the default configuration file if it does not exist."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
            log("Default configuration created and saved as 'config.json'.")
        except Exception as e:
            log(f"Failed to create default configuration: {e}", "ERROR")

    def load(self):
        """Load configuration from file, or use defaults if not found."""
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
            log("Configuration loaded successfully.")
        except OSError as e:
            if e.args[0] == 2:  # ENOENT error, file not found
                log("Configuration file not found, using default values and creating it.", "WARNING")
                self.save_default_config()
            else:
                log(f"Failed to load configuration: {e}", "ERROR")
        except Exception as e:
            log(f"Failed to load configuration: {e}", "ERROR")


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
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password)
        log(f"Access Point {self.ssid} started")

        # Wait until the AP gets an IP address
        while not self.ap.active():
            log("Waiting for AP to become active...", "WARNING")
            time.sleep(1)

        # Print the AP's IP address configuration
        ap_ip = self.ap.ifconfig()
        log(f"AP IP configuration: {ap_ip}")


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
        self.lock = asyncio.Lock()  # Lock for concurrent DNS access

    async def run(self):
        """Run the DNS server to handle incoming DNS requests"""
        self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udps.setblocking(False)  # Set the socket to non-blocking mode
        try:
            self.udps.bind(('0.0.0.0', 53))
            log("DNS server started on port 53")

            while True:
                try:
                    await self.handle_dns(self.udps)
                except asyncio.CancelledError:
                    log("DNS server task cancelled, shutting down...", "WARNING")
                    break
                except Exception as e:
                    log(f"Error handling DNS query: {e}", "ERROR")
                    await asyncio.sleep(1)
        except OSError as e:
            log(f"Failed to bind DNS server on port 53: {e}", "ERROR")
            raise
        finally:
            if self.udps:
                log("Closing DNS server socket...")
                self.udps.close()  # Ensure socket is closed to release resources
                log("DNS server socket closed.")

    async def handle_dns(self, sock):
        """Handle DNS requests with a polling approach and controlled access"""
        async with self.lock:
            try:
                # Try receiving data from the socket, non-blocking
                data, addr = sock.recvfrom(4096)
                DNS = DNSQuery(data)
                log(f"Received DNS query for domain: {DNS.domain}")
                sock.sendto(DNS.response(self.server_ip), addr)
                log(f"Replying: {DNS.domain} -> {self.server_ip}")
            except asyncio.CancelledError:
                log("DNS handling task cancelled gracefully.", "WARNING")
            except OSError as e:
                if e.args[0] == 11:  # EAGAIN or no data received yet
                    await asyncio.sleep(0)  # Yield control back to the event loop
                else:
                    log(f"Unexpected error in DNS handling: {e}", "ERROR")
                    raise
            except Exception as e:
                log(f"General error in DNS handling: {e}", "ERROR")
                await asyncio.sleep(1)


################################################################################
# Class to build an HTTP Server with Optional TLS Support
# and Optional File Serving Support
################################################################################
class HTTPServer:
    def __init__(self, cert_file='cert.pem', key_file='private.key', index_file='index.html'):
        self.cert_file = cert_file
        self.key_file = key_file
        self.index_file = index_file
        self.server = None
        self.use_tls = self.check_tls_support()
        self.has_index_file = self.check_index_file()

    def check_tls_support(self):
        """Check if both the certificate and key files are present using os.stat()."""
        try:
            os.stat(self.cert_file)
            os.stat(self.key_file)
            log("TLS support available: certificate and key files found.")
            return True
        except OSError:
            log("TLS support not available: certificate and/or key files missing. Falling back to HTTP.")
            return False

    def check_index_file(self):
        """Check if the index file exists in the filesystem."""
        try:
            os.stat(self.index_file)
            log(f"Index file '{self.index_file}' found. Serving it as the main page.")
            return True
        except OSError:
            log(f"Index file '{self.index_file}' not found. Falling back to default HTML content.", "WARNING")
            return False

    async def handle_connection(self, reader, writer):
        gc.collect()
        log("Handling HTTP request")

        # Read the HTTP request
        request_line = await reader.readline()
        log(f"Request: {request_line}")

        # Serve index.html if present, otherwise serve a default HTML page
        if b'GET /' in request_line:
            if self.has_index_file:
                # Serve the contents of index.html
                try:
                    with open(self.index_file, 'r') as file:
                        response_body = file.read()
                    response = 'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n' + response_body
                except Exception as e:
                    # Fallback to default HTML if there's an error reading index.html
                    log(f"Error reading {self.index_file}: {e}. Falling back to default content.", "ERROR")
                    response = self.get_default_html_response()
            else:
                # Serve the default HTML page
                response = self.get_default_html_response()
        else:
            response = 'HTTP/1.0 404 Not Found\r\n\r\n'

        await writer.awrite(response)
        await writer.aclose()
        gc.collect()

    def get_default_html_response(self):
        """Return the default HTML response when index.html is not found."""
        response = 'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n'
        response += "<html><head><title>ESP32 Captive Portal</title></head><body>"
        response += "<h1>Welcome to the ESP32 Captive Portal</h1>"
        response += "<p>You are now connected to the captive portal. Enjoy!</p>"
        response += "</body></html>"
        return response

    async def start(self):
        """Start the HTTP/HTTPS server depending on the availability of TLS."""
        try:
            if self.use_tls:
                # Create an SSL context and start HTTPS server
                context = tls.SSLContext(tls.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(self.cert_file, self.key_file)
                log("Creating TLS wrapped socket...")

                # Start the HTTPS server
                log("Starting HTTPS server on port 443...")
                self.server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 443, ssl=context)
                log("HTTPS server started on port 443.")
            else:
                # Start a plain HTTP server
                log("Starting HTTP server on port 80...")
                self.server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 80)
                log("HTTP server started on port 80.")
        except asyncio.CancelledError:
            log("HTTP server task cancelled gracefully.", "WARNING")

    async def close_server(self):
        """Gracefully close the HTTP/HTTPS server if it exists."""
        if self.server:
            log("Closing HTTP/HTTPS server...")
            self.server.close()
            await self.server.wait_closed()
            log("HTTP/HTTPS server closed successfully.")
            self.server = None


################################################################################
# Putting the whole captive portal together
################################################################################
class CaptivePortal:
    def __init__(self, config):
        self.wifi_ap = WiFiAccessPoint(config["ssid"], config["password"])
        self.dns_server = DNSServer(config["server_ip"])
        self.http_server = HTTPServer()  # Using HTTPServer with optional TLS support
        self.dns_task = None
        self.http_task = None

    async def start(self):
        # Start the Wi-Fi Access Point
        self.wifi_ap.start()

        # Start DNS and HTTP in background without blocking event loop
        log("Starting DNS and HTTP servers in parallel...")
        self.dns_task = asyncio.create_task(self.dns_server.run())  # DNS server in background
        self.http_task = asyncio.create_task(self.http_server.start())  # HTTP/HTTPS server in background

        # Enable watchdog timer to prevent hangs or crashes
        wdt = machine.WDT(timeout=10000)  # 10 seconds watchdog timeout
        log("Watchdog timer enabled.")

        # Keep the main task running indefinitely and feed the watchdog
        try:
            while True:
                wdt.feed()  # Feed the watchdog to prevent reset
                await asyncio.sleep(5)  # Sleep for a while before next feed
        except asyncio.CancelledError:
            log("Main loop task cancelled, stopping services...", "WARNING")

    async def stop(self):
        """Stop all servers and release resources."""
        log("Stopping Captive Portal...")
        # Cancel tasks and ensure they are awaited
        if self.http_task:
            log("Cancelling HTTP server task...")
            self.http_task.cancel()  # Cancel the HTTP/HTTPS task
            try:
                await asyncio.wait_for(self.http_task, timeout=5)
            except asyncio.TimeoutError:
                log("HTTP task timed out during cancellation.", "WARNING")
            except asyncio.CancelledError:
                log("HTTP task was cancelled.", "WARNING")

        if self.dns_task:
            log("Cancelling DNS server task...")
            self.dns_task.cancel()  # Cancel the DNS task
            try:
                await asyncio.wait_for(self.dns_task, timeout=5)
            except asyncio.TimeoutError:
                log("DNS task timed out during cancellation.", "WARNING")
            except asyncio.CancelledError:
                log("DNS task was cancelled.", "WARNING")

        # Close the HTTP server
        await self.http_server.close_server()
        log("Captive Portal stopped.")


################################################################################
# Main Loop with Configuration
################################################################################
# Load configuration
config = Configuration()
config.load()

# Instantiate Portal and run
portal = CaptivePortal(config.config)

try:
    log("Starting event loop...")
    if IS_UASYNCIO_V3:
        asyncio.run(portal.start())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(portal.start())

except Exception as e:
    log(f'An exception occurred: {e}', "ERROR")

except KeyboardInterrupt:
    log('Keyboard Interrupt detected. Shutting down...', "WARNING")

finally:
    if IS_UASYNCIO_V3:
        asyncio.run(portal.stop())  # Ensure all servers are closed