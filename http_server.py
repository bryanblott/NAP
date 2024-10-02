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
################################################################################


################################################################################
# Dependencies
################################################################################
import os
import gc
import tls
import uasyncio as asyncio
from logging_utility import log


################################################################################
# Code
################################################################################
class HTTPServer:
    def __init__(self, cert_file='cert.pem', key_file='private.key', root_directory='www'):
        self.cert_file = cert_file
        self.key_file = key_file
        self.root_directory = root_directory
        self.server = None
        self.use_tls = self.check_tls_support()
        self.shutdown_event = asyncio.Event()  # Event to signal shutdown

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
        log("Handling HTTP request")

        try:
            # Read the HTTP request with a timeout to prevent indefinite blocking
            request_line = await asyncio.wait_for(reader.readline(), timeout=5)  # 5-second timeout for reading request
            log(f"Request: {request_line}")

            # Parse request and extract path
            try:
                path = request_line.split()[1].decode('utf-8')
            except IndexError:
                path = '/'

            # Serve files from root_directory or default HTML if not found
            if path == '/':
                path = '/index.html'  # Default to index.html
            file_path = self.root_directory + path

            # Try to serve the requested file
            try:
                with open(file_path, 'rb') as file:
                    response_body = file.read()
                content_type = self.get_content_type(file_path)
                response = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n'
                await writer.awrite(response.encode('utf-8') + response_body)
            except OSError:
                # Fallback to 404 if file not found
                log(f"File not found: {file_path}. Responding with 404.", "ERROR")
                response = 'HTTP/1.0 404 Not Found\r\n\r\n'
                await writer.awrite(response.encode('utf-8'))
        except asyncio.TimeoutError:
            log("HTTP request reading timed out.", "WARNING")
        except asyncio.CancelledError:
            log("HTTP request handler was cancelled.", "WARNING")
        except Exception as e:
            log(f"General error while handling HTTP request: {e}", "ERROR")
        finally:
            # Ensure writer is closed properly
            try:
                await writer.aclose()
            except Exception as e:
                log(f"Error closing writer: {e}", "ERROR")
            gc.collect()

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

            # Wait for the shutdown event to be triggered
            await self.shutdown_event.wait()
            log("Shutdown event triggered, stopping server...")
        except asyncio.CancelledError:
            log("HTTP server task was cancelled gracefully.", "WARNING")
        except Exception as e:
            log(f"Error starting HTTP server: {e}", "ERROR")
        finally:
            await self.close_server()

    async def close_server(self):
        """Gracefully close the HTTP/HTTPS server if it exists."""
        if self.server:
            log("Closing HTTP/HTTPS server...")
            self.server.close()
            await self.server.wait_closed()
            log("HTTP/HTTPS server closed successfully.")
            self.server = None

    def trigger_shutdown(self):
        """Trigger the shutdown event to stop the server."""
        self.shutdown_event.set()
