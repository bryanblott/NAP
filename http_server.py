# Adding additional debug logging to http_server.py for better tracking

import tls
import usocket as socket
import uasyncio as asyncio
import os
import json
import gc

print("[INFO] HTTPServer: Available attributes in tls module:", dir(tls))

class HTTPServer:
    def __init__(self, cert_file='cert.pem', key_file='private.key', root_directory='www', host="0.0.0.0", port=80, wifi_client=None):
        self.cert_file = cert_file
        self.key_file = key_file
        self.root_directory = root_directory
        self.host = host
        self.port = port
        self.server_socket = None
        self.server_ip = host
        self.wifi_client = wifi_client
        self.use_tls = self.check_tls_support()
        self.shutdown_event = asyncio.Event()  # Event to signal shutdown
        print(f"[INFO] HTTPServer initialized with host: {self.host}, port: {self.port}, root_directory: {self.root_directory}")

    def check_tls_support(self):
        """Check if both the certificate and key files are present using os.stat()."""
        try:
            os.stat(self.cert_file)
            os.stat(self.key_file)
            print("[INFO] TLS support available: certificate and key files found.")
            return True
        except OSError:
            print("[WARNING] TLS support not available: certificate and/or key files missing. Falling back to HTTP.")
            return False

    async def start(self):
        """Start the HTTP or HTTPS server depending on the availability of TLS."""
        try:
            addr = (self.host, self.port)
            print(f"[DEBUG] Creating server socket with address: {addr}")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(addr)
            self.server_socket.listen(5)
            self.server_socket.setblocking(False)  # Ensure non-blocking mode
            print(f"[INFO] HTTPServer: Server started on {self.host}:{self.port}")

            # Wrap the socket in TLS if supported
            if self.use_tls:
                try:
                    print("[DEBUG] Attempting to create SSL context for TLS.")
                    context = tls.SSLContext(tls.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
                    print("[DEBUG] Wrapping server socket with SSL context.")
                    self.server_socket = context.wrap_socket(self.server_socket, server_side=True)
                    print("[INFO] HTTPServer: Server running in HTTPS mode.")
                except Exception as e:
                    print(f"[ERROR] HTTPServer: Failed to create SSL context or wrap socket: {e}")

            while True:
                try:
                    print("[DEBUG] HTTPServer: Waiting for new connections...")
                    conn, addr = await self.accept_connection()
                    print(f"[INFO] HTTPServer: Accepted new connection from {addr}.")
                    asyncio.create_task(self.handle_connection(conn))
                except asyncio.CancelledError:
                    print("[INFO] HTTPServer: Server stop requested.")
                    break
                except Exception as e:
                    print(f"[ERROR] HTTPServer: Error accepting connection: {e}")
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[ERROR] HTTPServer: Error starting server: {e}")
        finally:
            await self.stop()

    async def accept_connection(self):
        while True:
            try:
                conn, addr = self.server_socket.accept()
                return conn, addr
            except OSError as e:
                if e.args[0] == 11:  # EAGAIN, try again
                    await asyncio.sleep(0.1)
                else:
                    raise

    async def handle_connection(self, conn):
        """Handle incoming HTTP connections and serve files or responses."""
        gc.collect()
        print("[INFO] Handling HTTP request")

        try:
            # Read the request line from the client
            request_line = conn.readline()
            if not request_line:
                print("[WARNING] No request line received, closing connection.")
                conn.close()
                return

            print(f"[INFO] Request: {request_line.decode('utf-8').strip()}")

            # Parse request and extract path
            try:
                path = request_line.split()[1].decode('utf-8')
                print(f"[DEBUG] Parsed path from request: {path}")
            except IndexError:
                path = '/'
                print("[WARNING] Failed to parse path from request, defaulting to root path.")

            # Handle special paths like /scan and /connect
            if path == "/scan":
                await self.handle_scan_request(conn)
            elif path == "/connect":
                await self.handle_connect_request(conn)
            else:
                await self.serve_static_file(conn, path)
        except Exception as e:
            print(f"[ERROR] HTTPServer: General error while handling request: {e}")
        finally:
            # Ensure the connection is closed properly
            try:
                conn.close()
                print("[INFO] Connection closed successfully.")
            except Exception as e:
                print(f"[ERROR] Error closing connection: {e}")
            gc.collect()

    async def handle_scan_request(self, conn):
        """Handle requests to scan for Wi-Fi networks."""
        if self.wifi_client:
            print("[DEBUG] Handling scan request for Wi-Fi networks.")
            networks = await self.wifi_client.scan_networks()
            response = json.dumps(networks)
            print(f"[INFO] Scanned Wi-Fi Networks: {response}")
            await self.send_response(conn, response, content_type="application/json")
        else:
            print("[ERROR] WiFiClient instance not found. Cannot scan networks.")
            await self.send_response(conn, '{"error": "WiFiClient not available"}', content_type="application/json")

    async def handle_connect_request(self, conn):
        """Handle requests to connect to a Wi-Fi network."""
        if not self.wifi_client:
            print("[ERROR] WiFiClient instance not found. Cannot connect to networks.")
            await self.send_response(conn, '{"error": "WiFiClient not available"}', content_type="application/json")
            return

        print("[DEBUG] Handling connect request to Wi-Fi network.")
        content_length = 0
        while True:
            header_line = conn.readline()
            print(f"[DEBUG] Received header line: {header_line.decode().strip()}")
            if header_line.startswith(b'Content-Length'):
                content_length = int(header_line.decode().split(":")[1].strip())
                print(f"[DEBUG] Parsed Content-Length: {content_length}")
            if header_line == b'\r\n':
                break

        post_data = conn.read(content_length)
        print(f"[INFO] Received POST data: {post_data.decode().strip()}")
        ssid, password = self.parse_post_data(post_data)
        print(f"[DEBUG] Parsed SSID: {ssid}, Password: {password}")
        success = await self.wifi_client.connect_to_network(ssid, password)
        response = "Connection successful" if success else "Connection failed"
        print(response)
        await self.send_response(conn, response)

    async def serve_static_file(self, conn, path):
        """Serve static files from the root directory."""
        print(f"[DEBUG] Serving static file for path: {path}")
        if path == "/":
            path = "/index.html"
        file_path = f"{self.root_directory}{path}"
        try:
            with open(file_path, 'rb') as file:
                response_body = file.read()
            content_type = self.get_content_type(file_path)
            response = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n'
            conn.send(response.encode('utf-8') + response_body)
            print(f"[INFO] Served file: {file_path}")
        except OSError:
            print(f"[ERROR] File not found: {file_path}. Responding with 404.")
            response = 'HTTP/1.0 404 Not Found\r\n\r\n<h1>404 Not Found</h1>'
            conn.send(response.encode('utf-8'))

    async def send_response(self, conn, response_body, content_type="text/plain"):
        """Send an HTTP response with the specified content."""
        print("[DEBUG] Sending response to client.")
        response = f'HTTP/1.0 200 OK\r\nContent-Type: {content_type}\r\n\r\n'
        conn.send(response.encode('utf-8') + response_body.encode('utf-8'))
        print("[INFO] Response sent successfully.")

    def get_content_type(self, file_path):
        """Determine the MIME type based on the file extension."""
        print(f"[DEBUG] Determining content type for file: {file_path}")
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

    async def close_server(self):
        """Gracefully closes the HTTP/HTTPS server."""
        if self.server_socket is not None:
            print("[INFO] HTTPServer: Closing server.")
            self.server_socket.close()
            print("[INFO] HTTPServer: Server closed successfully.")

    async def stop(self):
        """Gracefully closes the HTTP/HTTPS server."""
        if self.server_socket is not None:
            print("[INFO] HTTPServer: Closing server.")
            self.server_socket.close()
            print("[INFO] HTTPServer: Server closed successfully.")


    async def restart_server(self):
        """Restart the HTTP server to apply new configurations or IP address changes."""
        print("[INFO] Restarting HTTP server.")
        await self.stop()
        await self.start()

    def update_server_ip(self, new_ip):
        """Update the IP address for the server and restart it with the new IP."""
        print(f"[INFO] Updating server IP to {new_ip} and restarting server.")
        self.host = new_ip
        asyncio.create_task(self.restart_server())