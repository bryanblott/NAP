################################################################################
# This module defines the HTTPServer class, which is responsible for starting 
# and managing an HTTP or HTTPS server on an ESP32 device. The server can serve 
# a specified index file or a default HTML page if the index file is not found. 
# It also supports TLS if the necessary certificate and key files are available.
#
# Classes:
#     HTTPServer: A class to handle HTTP/HTTPS server operations, including 
#     checking for TLS support, serving files, and managing connections.
#
# Methods:
#     __init__(self, cert_file='cert.pem', key_file='private.key', index_file='index.html'):
#         Initializes the HTTPServer instance with the specified certificate, 
#         key, and index files.
#
#     check_tls_support(self):
#         Checks if both the certificate and key files are present to determine 
#         TLS support.
#
#     check_index_file(self):
#         Checks if the index file exists in the filesystem.
#
#     async handle_connection(self, reader, writer):
#         Handles incoming HTTP requests and serves the appropriate response.
#
#     get_default_html_response(self):
#         Returns the default HTML response when the index file is not found.
#
#     async start(self):
#         Starts the HTTP or HTTPS server depending on the availability of TLS.
#
#     async close_server(self):
#         Gracefully closes the HTTP/HTTPS server if it exists.
#
#     update_server_ip(self, new_ip):
#         Updates the IP address for the server and restarts it with the new IP.
#
#     restart_server(self):
#         Restarts the HTTP server with the updated IP address.
################################################################################

################################################################################
# Dependencies
################################################################################
import uasyncio as asyncio
import os
import json
import gc
import tls
from logging_utility import create_logger

# Setup logging
logger = create_logger("HTTPServer")


class HTTPServer:
    def __init__(self, cert_file='cert.pem', key_file='private.key', root_directory='www', host="0.0.0.0", port=80, wifi_client=None):
        self.cert_file = cert_file
        self.key_file = key_file
        self.root_directory = root_directory
        self.host = host
        self.port = port
        self.server = None
        self.server_ip = host
        self.wifi_client = wifi_client
        self.use_tls = self.check_tls_support()
        self.shutdown_event = asyncio.Event()  # Event to signal shutdown

    def check_tls_support(self):
        """Check if both the certificate and key files are present using os.stat()."""
        try:
            os.stat(self.cert_file)
            os.stat(self.key_file)
            logger.info("TLS support available: certificate and key files found.")
            return True
        except OSError:
            logger.warning("TLS support not available: certificate and/or key files missing. Falling back to HTTP.")
            return False

    def get_content_type(self, file_path):
        """Determine the MIME type based on the file extension."""
        if file_path.endswith('.html'):
            return 'text/html'
        elif file_path.endswith('.css'):
            return 'text/css'
        elif file_path.endswith('.js'):
            return 'application/javascript'
        elif file_path.endswith('.png'):
            return 'image/png'
        elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
            return 'image/jpeg'
        elif file_path.endswith('.gif'):
            return 'image/gif'
        else:
            return 'text/plain'

    async def handle_connection(self, reader, writer):
        """Handle incoming HTTP connections and serve files or responses."""
        gc.collect()
        logger.info("Handling HTTP request")

        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=5)  # 5-second timeout for reading request
            logger.info(f"Request: {request_line}")

            # Parse request and extract path
            try:
                path = request_line.split()[1].decode('utf-8')
            except IndexError:
                path = '/'

            # Handle requests to /scan and /connect
            if path == "/scan":
                await self.handle_scan_request(writer)
            elif path == "/connect":
                await self.handle_connect_request(reader, writer)
            else:
                await self.serve_static_file(writer, path)
        except asyncio.TimeoutError:
            logger.warning("HTTP request reading timed out.")
        except asyncio.CancelledError:
            logger.warning("HTTP request handler was cancelled.")
        except Exception as e:
            logger.error(f"General error while handling HTTP request: {e}")
        finally:
            # Ensure writer is closed properly
            try:
                await writer.aclose()
            except Exception as e:
                logger.error(f"Error closing writer: {e}")
            gc.collect()

    async def handle_scan_request(self, writer):
        """Handle requests to scan for Wi-Fi networks."""
        if self.wifi_client:
            networks = await self.wifi_client.scan_networks()
            response = json.dumps(networks)
            logger.info(f"Scanned Wi-Fi Networks: {response}")
            await self.send_response(writer, response, content_type="application/json")
        else:
            logger.error("WiFiClient instance not found. Cannot scan networks.")
            await self.send_response(writer, '{"error": "WiFiClient not available"}', content_type="application/json")

    async def handle_connect_request(self, reader, writer):
        """Handle requests to connect to a Wi-Fi network."""
        if not self.wifi_client:
            logger.error("WiFiClient instance not found. Cannot connect to networks.")
            await self.send_response(writer, '{"error": "WiFiClient not available"}', content_type="application/json")
            return

        content_length = 0
        while True:
            header_line = await reader.readline()
            if header_line.startswith(b'Content-Length'):
                content_length = int(header_line.decode().split(":")[1].strip())
            if header_line == b'\r\n':
                break

        post_data = await reader.read(content_length)
        ssid, password = self.parse_post_data(post_data)
        success = await self.wifi_client.connect_to_network(ssid, password)
        response = "Connection successful" if success else "Connection failed"
        logger.info(response)
        await self.send_response(writer, response)

    async def serve_static_file(self, writer, path):
        """Serve static files from the root directory."""
        if path == "/":
            path = "/index.html"
        file_path = f"{self.root_directory}{path}"
        try:
            with open(file_path, 'rb') as file:
                response_body = file.read()
            content_type = self.get_content_type(file_path)
            response = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n'
            await writer.awrite(response.encode('utf-8') + response_body)
        except OSError:
            logger.error(f"File not found: {file_path}. Responding with 404.")
            response = 'HTTP/1.0 404 Not Found\r\n\r\n<h1>404 Not Found</h1>'
            await writer.awrite(response.encode('utf-8'))

    async def send_response(self, writer, response_body, content_type="text/plain"):
        """Send an HTTP response with the specified content."""
        response = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n'
        await writer.awrite(response.encode('utf-8') + response_body.encode('utf-8'))

    async def start(self):
        """Start the HTTP/HTTPS server depending on the availability of TLS."""
        try:
            if self.use_tls:
                context = tls.SSLContext(tls.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(self.cert_file, self.key_file)
                logger.info("Starting HTTPS server on port 443...")
                self.server = await asyncio.start_server(self.handle_connection, self.host, 443, ssl=context)
                logger.info("HTTPS server started.")
            else:
                logger.info(f"Starting HTTP server on {self.host}:{self.port}...")
                self.server = await asyncio.start_server(self.handle_connection, self.host, self.port)
                logger.info(f"HTTP server started on {self.host}:{self.port}.")

            await self.shutdown_event.wait()
        except asyncio.CancelledError:
            logger.warning("HTTP server task was cancelled gracefully.")
        except Exception as e:
            logger.error(f"Error starting HTTP server: {e}")

    async def stop(self):
        """Stop the HTTP server gracefully."""
        if self.server:
            logger.info("Stopping HTTP server...")
            self.server.close()
            await self.server.wait_closed()
            logger.info("HTTP server stopped successfully.")
            self.server = None

    async def restart_server(self):
        """Restart the HTTP server to apply new configurations or IP address changes."""
        await self.stop()
        await self.start()

    def update_server_ip(self, new_ip):
        """Update the IP address for the server and restart it with the new IP."""
        self.host = new_ip
        asyncio.create_task(self.restart_server())
