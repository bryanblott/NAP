import uasyncio as asyncio
import os

try:
    import tls
except ImportError:
    print("[WARNING] tls module not available, falling back to non-TLS mode")
    tls = None

class HTTPServer:
    def __init__(self, root_directory='www', host="0.0.0.0", port=80, ssl_certfile='cert.pem', ssl_keyfile='private.key'):
        self.root_directory = root_directory
        self.host = host
        self.port = port
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.server = None
        self.use_tls = self.check_tls_files()
        self.running = False
        self.interface_manager = None

    def set_interface_manager(self, interface_manager):
        self.interface_manager = interface_manager

    def check_tls_files(self):
        try:
            os.stat(self.ssl_certfile)
            os.stat(self.ssl_keyfile)
            if tls is None:
                print("[WARNING] TLS files found, but tls module not available. Falling back to HTTP.")
                return False
            return True
        except OSError:
            print("[WARNING] TLS certificate or key file not found. Falling back to HTTP.")
            return False

    async def start(self):
        print(f"[DEBUG] HTTP(S) Server: Starting on {self.host}:{self.port}")
        try:
            if self.use_tls:
                context = tls.SSLContext(tls.PROTOCOL_TLS_SERVER)
                try:
                    context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
                except Exception as e:
                    print(f"[ERROR] Failed to load TLS cert/key: {e}")
                    print("[WARNING] Falling back to HTTP")
                    self.use_tls = False

            if self.use_tls:
                self.server = await asyncio.start_server(self.handle_request, self.host, self.port, ssl=context)
                print(f"[INFO] HTTPS Server: Started on {self.host}:{self.port}")
            else:
                self.server = await asyncio.start_server(self.handle_request, self.host, self.port)
                print(f"[INFO] HTTP Server: Started on {self.host}:{self.port}")
            self.running = True
        except Exception as e:
            print(f"[ERROR] HTTP(S) Server: Failed to start: {e}")
            self.running = False

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
        print("[INFO] HTTP(S) Server: Stopped")

    async def restart(self):
        print("[INFO] HTTP(S) Server: Restarting...")
        await self.stop()
        await asyncio.sleep(1)  # Give a short delay before restarting
        await self.start()
        print("[INFO] HTTP(S) Server: Restarted successfully")

    async def handle_request(self, reader, writer):
        try:
            request_line = await reader.readline()
            print(f"[DEBUG] HTTP(S) Server: Received request: {request_line}")
            
            # Parse the request
            method, path, _ = request_line.decode().strip().split(' ', 2)
            print(f"[DEBUG] Parsed request - Method: {method}, Path: {path}")
            
            if path == '/' or path == '/index.html':
                print("[DEBUG] Serving index.html")
                await self.serve_file('index.html', writer)
            elif path == '/styles.css':
                print("[DEBUG] Serving styles.css")
                await self.serve_file('styles.css', writer)
            elif path == '/script.js':
                print("[DEBUG] Serving script.js")
                await self.serve_file('script.js', writer)
            elif path == '/scan':
                print("[DEBUG] Handling scan request")
                await self.handle_scan_request(writer)
            elif path == '/connect':
                print("[DEBUG] Handling connect request")
                await self.handle_connect_request(reader, writer)
            else:
                print(f"[DEBUG] Unrecognized path: {path}")
                response = "HTTP/1.0 404 Not Found\r\n\r\nNot Found"
                writer.write(response.encode('utf-8'))
            
            await writer.drain()
        except Exception as e:
            print(f"[ERROR] HTTP(S) Server: Error handling request: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve_file(self, path, writer):
        try:
            full_path = f"{self.root_directory}/{path}"
            print(f"[DEBUG] Attempting to serve file: {full_path}")
            with open(full_path, "rb") as file:
                content = file.read()
                writer.write(b"HTTP/1.0 200 OK\r\n")
                if path.endswith('.html'):
                    writer.write(b"Content-Type: text/html\r\n")
                elif path.endswith('.css'):
                    writer.write(b"Content-Type: text/css\r\n")
                elif path.endswith('.js'):
                    writer.write(b"Content-Type: application/javascript\r\n")
                else:
                    writer.write(b"Content-Type: text/plain\r\n")
                writer.write(f"Content-Length: {len(content)}\r\n\r\n".encode('utf-8'))
                writer.write(content)
            print(f"[DEBUG] File served successfully: {full_path}")
        except OSError as e:
            print(f"[ERROR] Failed to serve file {path}: {e}")
            response = f"HTTP/1.0 404 Not Found\r\n\r\nFile not found: {path}"
            writer.write(response.encode('utf-8'))
        await writer.drain()

    async def handle_scan_request(self, writer):
        print("[DEBUG] Handling scan request")
        if self.interface_manager:
            try:
                sta_interface = self.interface_manager.interfaces.get('sta')
                if sta_interface:
                    print("[DEBUG] STA interface found, initiating scan")
                    networks = await sta_interface.scan_networks()
                    if networks:
                        response_data = ','.join(networks)
                        print(f"[DEBUG] Scan results: {response_data}")
                        response = f"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response_data)}\r\n\r\n{response_data}"
                    else:
                        print("[DEBUG] No networks found")
                        response = "HTTP/1.0 204 No Content\r\n\r\n"
                else:
                    print("[ERROR] STA interface not available")
                    response = "HTTP/1.0 500 Internal Server Error\r\n\r\nSTA interface not available"
            except Exception as e:
                print(f"[ERROR] Failed to scan networks: {e}")
                response = "HTTP/1.0 500 Internal Server Error\r\n\r\nFailed to scan networks"
        else:
            print("[ERROR] InterfaceManager not available")
            response = "HTTP/1.0 500 Internal Server Error\r\n\r\nInterfaceManager not available"
        
        writer.write(response.encode('utf-8'))
        await writer.drain()
        print("[DEBUG] Scan response sent")

    async def handle_connect_request(self, reader, writer):
        print("[DEBUG] Handling connect request")
        if self.interface_manager:
            try:
                # Read the POST data
                content_length = 0
                while True:
                    line = await reader.readline()
                    if line.startswith(b'Content-Length:'):
                        content_length = int(line.split(b':')[1])
                    if line == b'\r\n':
                        break
                
                post_data = await reader.read(content_length)
                data = post_data.decode('utf-8')
                params = {}
                for param in data.split('&'):
                    key, value = param.split('=')
                    params[key] = self.url_decode(value)
                
                ssid = params.get('ssid', '')
                password = params.get('password', '')
                
                if ssid and password:
                    print(f"[DEBUG] Attempting to connect to SSID: {ssid}")
                    sta_interface = self.interface_manager.interfaces.get('sta')
                    if sta_interface:
                        success = await sta_interface.connect(ssid, password)
                        if success:
                            response = "HTTP/1.0 200 OK\r\n\r\nConnected successfully"
                        else:
                            response = "HTTP/1.0 400 Bad Request\r\n\r\nFailed to connect"
                    else:
                        response = "HTTP/1.0 500 Internal Server Error\r\n\r\nSTA interface not available"
                else:
                    response = "HTTP/1.0 400 Bad Request\r\n\r\nMissing SSID or password"
            except Exception as e:
                print(f"[ERROR] Failed to connect to network: {e}")
                response = "HTTP/1.0 500 Internal Server Error\r\n\r\nFailed to connect to network"
        else:
            print("[ERROR] InterfaceManager not available")
            response = "HTTP/1.0 500 Internal Server Error\r\n\r\nInterfaceManager not available"
        
        writer.write(response.encode('utf-8'))
        await writer.drain()

    def url_decode(self, s):
        """Simple URL decoding function"""
        return s.replace('%20', ' ').replace('+', ' ')