# http_server.py
import uasyncio as asyncio
import tls
import gc
import os
from logging_utility import log

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
