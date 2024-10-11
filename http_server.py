import uasyncio as asyncio
import ujson

try:
    import ssl
except ImportError:
    print("[WARNING] ssl module not available, falling back to non-TLS mode")
    ssl = None

def join_path(*args):
    return '/'.join(arg.strip('/') for arg in args)

class HTTPServer:
    def __init__(self, root_directory='www', ports=[80], ssl_ports=[443], ssl_certfile='cert.pem', ssl_keyfile='private.key'):
        self.root_directory = root_directory
        self.ports = ports
        self.ssl_ports = ssl_ports
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.servers = []
        self.use_tls = self.check_tls_files()
        self.running = False
        self.interface_manager = None

    def set_interface_manager(self, interface_manager):
        self.interface_manager = interface_manager

    def check_tls_files(self):
        try:
            with open(self.ssl_certfile, 'r'):
                pass
            with open(self.ssl_keyfile, 'r'):
                pass
            if ssl is None:
                print("[WARNING] TLS files found, but ssl module not available. Falling back to HTTP.")
                return False
            return True
        except OSError:
            print("[WARNING] TLS certificate or key file not found. Falling back to HTTP.")
            return False

    async def start(self):
        print(f"[DEBUG] HTTP(S) Server: Starting on HTTP ports {self.ports} and HTTPS ports {self.ssl_ports}")
        try:
            # Start non-SSL servers
            for port in self.ports:
                server = await asyncio.start_server(self.handle_request, "0.0.0.0", port)
                self.servers.append(server)
                print(f"[INFO] HTTP Server: Started on port {port}")

            # Start SSL servers if TLS is available
            if self.use_tls:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                try:
                    context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
                    for port in self.ssl_ports:
                        ssl_server = await asyncio.start_server(self.handle_request, "0.0.0.0", port, ssl=context)
                        self.servers.append(ssl_server)
                        print(f"[INFO] HTTPS Server: Started on port {port}")
                except Exception as e:
                    print(f"[ERROR] Failed to load TLS cert/key: {e}")
                    print("[WARNING] Falling back to HTTP only")
                    self.use_tls = False

            self.running = True
        except Exception as e:
            print(f"[ERROR] HTTP(S) Server: Failed to start: {e}")
            self.running = False

    async def stop(self):
        for server in self.servers:
            server.close()
            await server.wait_closed()
        self.servers = []
        self.running = False
        print("[INFO] HTTP(S) Server: Stopped")

    async def restart(self):
        print("[INFO] HTTP(S) Server: Restarting...")
        await self.stop()
        await asyncio.sleep(1)  # Give a short delay before restarting
        await self.start()
        print("[INFO] HTTP(S) Server: Restarted successfully")

    def get_client_interface(self, client_address):
        if self.interface_manager:
            ap_interface = self.interface_manager.interfaces.get('ap')
            sta_interface = self.interface_manager.interfaces.get('sta')
            
            if ap_interface and ap_interface.is_connected():
                ap_ip = ap_interface.get_ip()
                if ap_ip and ap_ip.split('.')[0:3] == client_address.split('.')[0:3]:
                    return 'ap', ap_ip

            if sta_interface and sta_interface.is_connected():
                sta_ip = sta_interface.get_ip()
                if sta_ip and sta_ip.split('.')[0:3] == client_address.split('.')[0:3]:
                    return 'sta', sta_ip

        return None, "0.0.0.0"

    async def handle_request(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                print("[WARNING] Empty request received")
                return

            print(f"[DEBUG] HTTP(S) Server: Received request: {request_line}")
            
            method, path, version = request_line.decode().strip().split(' ', 2)
            print(f"[DEBUG] Parsed request - Method: {method}, Path: {path}")
            
            client_address = writer.get_extra_info('peername')[0]
            client_interface, server_ip = self.get_client_interface(client_address)
            
            print(f"[DEBUG] Client connected via {client_interface} interface")

            if method == 'CONNECT':
                print(f"[DEBUG] Received CONNECT request for {path}")
                response = "HTTP/1.1 200 Connection Established\r\n\r\n"
                writer.write(response.encode('utf-8'))
                await writer.drain()
                return

            # Handle specific requests regardless of client interface
            if path == '/scan':
                print("[DEBUG] Routing to handle_scan_request")
                await self.handle_scan_request(writer)
                return
            elif path == '/connect' and method == 'POST':
                print("[DEBUG] Routing to handle_connect_request")
                await self.handle_connect_request(reader, writer)
                return

            # Handle captive portal detection and redirects only for AP clients
            if client_interface == 'ap':
                if self.is_captive_portal_request(path):
                    await self.captive_portal_redirect(writer, server_ip)
                    return
                elif path != '/' and path != '/index.html' and '.' not in path:
                    await self.captive_portal_redirect(writer, server_ip)
                    return

            # Normal request handling for both AP and STA clients
            if path == '/' or path == '/index.html':
                print("[DEBUG] Serving index.html")
                await self.serve_file('index.html', writer)
            elif path.startswith('/'):
                print(f"[DEBUG] Serving file: {path[1:]}")
                await self.serve_file(path[1:], writer)
            else:
                print(f"[DEBUG] Unrecognized path: {path}")
                response = "HTTP/1.0 404 Not Found\r\n\r\nNot Found"
                writer.write(response.encode('utf-8'))
            
            await writer.drain()
        except Exception as e:
            print(f"[ERROR] HTTP(S) Server: Error handling request: {e}")
        finally:
            await writer.wait_closed()

    def is_captive_portal_request(self, path):
        captive_portal_paths = [
            '/generate_204',
            '/hotspot-detect.html',
            '/connecttest.txt',
            '/redirect',
            '/success.txt',
            '/ncsi.txt',
        ]
        return path in captive_portal_paths

    async def captive_portal_redirect(self, writer, server_ip):
        port = self.ports[0] if self.ports else 80
        location = f"http://{server_ip}:{port}/index.html"
        response = f"HTTP/1.1 307 Temporary Redirect\r\nLocation: {location}\r\nCache-Control: no-cache\r\n\r\n"
        writer.write(response.encode())
        await writer.drain()
        print(f"[DEBUG] Captive Portal: Redirected to: {location}")

    async def serve_file(self, path, writer):
        try:
            full_path = join_path(self.root_directory, path)
            print(f"[DEBUG] Attempting to serve file: {full_path}")
            
            try:
                with open(full_path, "rb") as file:
                    content = file.read()
            except OSError:
                print(f"[ERROR] File not found: {full_path}")
                response = f"HTTP/1.0 404 Not Found\r\n\r\nFile not found: {path}"
                writer.write(response.encode('utf-8'))
                return

            writer.write(b"HTTP/1.0 200 OK\r\n")
            content_type = self.get_content_type(path)
            writer.write(f"Content-Type: {content_type}\r\n".encode('utf-8'))
            writer.write(f"Content-Length: {len(content)}\r\n".encode('utf-8'))
            writer.write(b"Cache-Control: no-cache\r\n")
            writer.write(b"\r\n")
            writer.write(content)
            print(f"[DEBUG] File served successfully: {full_path}")
        except Exception as e:
            print(f"[ERROR] Failed to serve file {path}: {e}")
            response = f"HTTP/1.0 500 Internal Server Error\r\n\r\nError serving file: {path}"
            writer.write(response.encode('utf-8'))
        await writer.drain()

    def get_content_type(self, path):
        if path.endswith('.html'):
            return 'text/html'
        elif path.endswith('.css'):
            return 'text/css'
        elif path.endswith('.js'):
            return 'application/javascript'
        else:
            return 'text/plain'

    async def handle_scan_request(self, writer):
        print("[DEBUG] Inside handle_scan_request")
        if self.interface_manager:
            try:
                sta_interface = self.interface_manager.interfaces.get('sta')
                if sta_interface:
                    print("[DEBUG] STA interface found, initiating scan")
                    networks = await sta_interface.scan_networks()
                    print(f"[DEBUG] Raw scan results: {networks}")
                    response_data = ujson.dumps({"networks": networks})
                    print(f"[DEBUG] JSON response: {response_data}")
                    headers = [
                        "HTTP/1.0 200 OK",
                        "Content-Type: application/json",
                        f"Content-Length: {len(response_data)}",
                        "Access-Control-Allow-Origin: *",
                        "",
                        ""
                    ]
                    response = "\r\n".join(headers).encode('utf-8') + response_data.encode('utf-8')
                else:
                    print("[ERROR] STA interface not available")
                    response = "HTTP/1.0 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{\"error\": \"STA interface not available\"}".encode('utf-8')
            except Exception as e:
                print(f"[ERROR] Failed to scan networks: {e}")
                response = f"HTTP/1.0 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{{\"error\": \"Failed to scan networks: {str(e)}\"}}".encode('utf-8')
        else:
            print("[ERROR] InterfaceManager not available")
            response = "HTTP/1.0 500 Internal Server Error\r\nContent-Type: application/json\r\n\r\n{\"error\": \"InterfaceManager not available\"}".encode('utf-8')
        
        print(f"[DEBUG] Sending response: {response}")
        writer.write(response)
        await writer.drain()
        print("[DEBUG] Scan response sent")
        
    async def handle_connect_request(self, reader, writer):
        print("[DEBUG] Handling connect request")
        if self.interface_manager:
            try:
                # Read headers
                headers = {}
                content_length = 0
                while True:
                    line = await reader.readline()
                    print(f"[DEBUG] Header line: {line}")
                    if line == b'\r\n':
                        break
                    if line == b'':
                        print("[ERROR] Unexpected end of request while reading headers")
                        break
                    try:
                        name, value = line.decode().strip().split(': ', 1)
                        headers[name.lower()] = value
                        if name.lower() == 'content-length':
                            content_length = int(value)
                    except ValueError:
                        print(f"[ERROR] Invalid header: {line}")

                print(f"[DEBUG] Headers: {headers}")
                print(f"[DEBUG] Content-Length: {content_length}")

                if content_length == 0:
                    print("[ERROR] Content-Length is 0, no POST data received")
                    response = "HTTP/1.0 400 Bad Request\r\n\r\nNo POST data received"
                else:
                    # Read POST data
                    post_data = await reader.read(content_length)
                    data = post_data.decode('utf-8')
                    print(f"[DEBUG] Raw POST data: {data}")

                    # Parse POST data
                    params = {}
                    for param in data.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key] = self.url_decode(value)
                        else:
                            print(f"[WARNING] Malformed parameter: {param}")

                    ssid = params.get('ssid', '')
                    password = params.get('password', '')

                    print(f"[DEBUG] Parsed SSID: {ssid}")
                    print(f"[DEBUG] Parsed Password (length): {len(password)}")

                    if ssid and password:
                        print(f"[DEBUG] Attempting to connect to SSID: {ssid}")
                        sta_interface = self.interface_manager.interfaces.get('sta')
                        if sta_interface:
                            print("[DEBUG] STA interface found")
                            # Temporarily disable auto-reconnect
                            print("[DEBUG] Disabling auto-reconnect")
                            self.interface_manager.disable_auto_reconnect()
                            try:
                                print("[DEBUG] Calling sta_interface.connect")
                                success = await sta_interface.connect(ssid, password)
                                print(f"[DEBUG] Connection attempt result: {success}")
                            except Exception as e:
                                print(f"[ERROR] Exception during connection attempt: {e}")
                                success = False
                            finally:
                                print("[DEBUG] Re-enabling auto-reconnect")
                                self.interface_manager.enable_auto_reconnect()
                            
                            if success:
                                ip_address = sta_interface.get_ip()
                                print(f"[DEBUG] Successfully connected. IP: {ip_address}")
                                response = f"HTTP/1.0 200 OK\r\n\r\nConnected successfully to {ssid}. IP: {ip_address}"
                            else:
                                print("[DEBUG] Connection failed")
                                response = "HTTP/1.0 400 Bad Request\r\n\r\nFailed to connect. Please check the SSID and password."
                        else:
                            print("[ERROR] STA interface not available")
                            response = "HTTP/1.0 500 Internal Server Error\r\n\r\nSTA interface not available"
                    else:
                        print("[ERROR] Missing SSID or password")
                        response = "HTTP/1.0 400 Bad Request\r\n\r\nMissing SSID or password"
            except Exception as e:
                print(f"[ERROR] Failed to process connect request: {e}")
                response = f"HTTP/1.0 500 Internal Server Error\r\n\r\nFailed to process connect request: {str(e)}"
        else:
            print("[ERROR] InterfaceManager not available")
            response = "HTTP/1.0 500 Internal Server Error\r\n\r\nInterfaceManager not available"

        print(f"[DEBUG] Sending response: {response}")
        writer.write(response.encode('utf-8'))
        await writer.drain()
        print(f"[DEBUG] Connect response sent: {response}")

    def url_decode(self, s):
        """Improved URL decoding function"""
        s = s.replace('+', ' ')
        s = s.split('%')
        res = s[0]
        for h in s[1:]:
            if len(h) > 2:
                res += chr(int(h[:2], 16)) + h[2:]
            elif len(h) == 2:
                res += chr(int(h, 16))
            else:
                res += '%' + h
        return res

    def is_running(self):
        return self.running