import uasyncio as asyncio
import ujson
from utils import log_with_timestamp  # Updated import
import json

try:
    import ssl
except ImportError:
    print("[WARNING] ssl module not available, falling back to non-TLS mode")
    ssl = None

def join_path(*args):
    return '/'.join(arg.strip('/') for arg in args)

def url_decode(s):
    log_with_timestamp(f"[DEBUG] url_decode input: {s}")
    result = ''
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                result += chr(int(s[i+1:i+3], 16))
                i += 3
            except ValueError:
                result += s[i]
                i += 1
        else:
            result += s[i]
            i += 1
    result = result.replace('+', ' ')
    log_with_timestamp(f"[DEBUG] url_decode output: {result}")
    return result

class HTTPServer:
    def __init__(self, interface_manager):
        self.interface_manager = interface_manager
        self.root_directory = 'www'
        self.ports = [80]
        self.ssl_ports = [443]
        self.ssl_certfile = 'cert.pem'
        self.ssl_keyfile = 'private.key'
        self.servers = []
        self.use_tls = self.check_tls_files()
        self.running = False
        self.max_concurrent_requests = 5
        self.current_requests = 0

    def check_tls_files(self):
        try:
            with open(self.ssl_certfile, 'r'):
                pass
            with open(self.ssl_keyfile, 'r'):
                pass
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
            while self.running:
                await asyncio.sleep(1)  # Cooperative yield
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
        log_with_timestamp("[DEBUG] HTTP(S) Server: Handling new request")
        try:
            request_line = await reader.readline()
            log_with_timestamp(f"[DEBUG] HTTP(S) Server: Received request: {request_line}")
            
            method, path, version = request_line.decode().strip().split(' ', 2)
            log_with_timestamp(f"[DEBUG] Parsed request - Method: {method}, Path: {path}")
            
            client_address = writer.get_extra_info('peername')[0]
            client_interface, server_ip = self.get_client_interface(client_address)
            
            log_with_timestamp(f"[DEBUG] Client connected via {client_interface} interface")

            if path == '/scan':
                await self.handle_scan_request(writer)
            elif path == '/connect' and method == 'POST':
                await self.handle_connect_request(reader, writer)
            elif path in ['/hotspot-detect.html', '/generate_204', '/ncsi.txt']:
                await self.handle_captive_portal_detection(writer, server_ip)
            elif path == '/index.html' or path == '/':
                await self.serve_file(writer, 'index.html')
            else:
                await self.serve_file(writer, path.lstrip('/'))

        except Exception as e:
            log_with_timestamp(f"[ERROR] HTTP(S) Server: Error handling request: {e}")
            writer.write(b"HTTP/1.0 500 Internal Server Error\r\n\r\nInternal Server Error")
        finally:
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            log_with_timestamp("[DEBUG] HTTP(S) Server: Connection closed")

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
        log_with_timestamp(f"[DEBUG] Captive Portal: Redirected to: {location}")

    async def serve_file(self, writer, path):
        try:
            full_path = join_path(self.root_directory, path)
            log_with_timestamp(f"[DEBUG] Attempting to serve file: {full_path}")
            
            try:
                with open(full_path, "rb") as file:
                    content = file.read()
            except OSError:
                log_with_timestamp(f"[ERROR] File not found: {full_path}")
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
            log_with_timestamp(f"[DEBUG] File served successfully: {full_path}")
        except Exception as e:
            log_with_timestamp(f"[ERROR] Failed to serve file {path}: {e}")
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
        log_with_timestamp("[DEBUG] Handling scan request")
        sta_interface = self.interface_manager.get_interface('sta')
        if sta_interface:
            try:
                networks = await sta_interface.scan_networks()
                log_with_timestamp(f"[DEBUG] Scanned networks: {networks}")
                response = json.dumps({"networks": networks})
                writer.write(f"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n{response}".encode())
            except Exception as e:
                log_with_timestamp(f"[ERROR] Failed to scan networks: {e}")
                writer.write(b"HTTP/1.0 500 Internal Server Error\r\n\r\nFailed to scan networks")
        else:
            log_with_timestamp("[ERROR] STA interface not available for scanning")
            writer.write(b"HTTP/1.0 500 Internal Server Error\r\n\r\nSTA interface not available")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    
    async def handle_connect_request(self, reader, writer):
        log_with_timestamp("[DEBUG] Handling connect request")
        response = "Internal Server Error"
        try:
            content_length = 0
            headers = {}
            while True:
                line = await reader.readline()
                if line == b'\r\n':
                    break
                if line.startswith(b'Content-Length:'):
                    content_length = int(line.split(b':')[1])
                headers[line.split(b':')[0].decode('utf-8').lower()] = line.split(b':')[1].strip().decode('utf-8')

            body = await reader.read(content_length)
            data = body.decode('utf-8')
            log_with_timestamp(f"[DEBUG] Raw request body: {data}")
            
            params = {}
            for param in data.split('&'):
                key, value = param.split('=')
                params[key] = value
                log_with_timestamp(f"[DEBUG] Raw parameter: {key} = {value}")

            ssid_raw = params.get('ssid', '')
            password_raw = params.get('password', '')
            log_with_timestamp(f"[DEBUG] Raw SSID: {ssid_raw}")
            log_with_timestamp(f"[DEBUG] Raw password: {password_raw}")

            ssid = url_decode(ssid_raw)
            password = url_decode(password_raw)

            log_with_timestamp(f"[DEBUG] Decoded SSID: '{ssid}'")
            log_with_timestamp(f"[DEBUG] Decoded password: '{password}'")

            if ssid and password:
                sta_interface = self.interface_manager.get_interface('sta')
                if sta_interface:
                    if sta_interface.is_connecting():
                        response = "Connection attempt already in progress"
                    else:
                        success = await sta_interface.connect(ssid, password)
                        if success:
                            # Get the IP address after successful connection
                            ip_address = sta_interface.get_ip()
                            response = f"Connected successfully to '{ssid}' with IP: {ip_address}"
                        else:
                            response = f"Failed to connect to '{ssid}'. Please check the password and try again."
                else:
                    response = "STA interface not available"
            else:
                response = "Missing SSID or password"

        except Exception as e:
            log_with_timestamp(f"[ERROR] Error in handle_connect_request: {e}")
            response = "Internal Server Error"

        try:
            writer.write(f"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\n{response}".encode())
            await writer.drain()
        except Exception as e:
            log_with_timestamp(f"[ERROR] Failed to send response: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                log_with_timestamp(f"[ERROR] Failed to close writer: {e}")
            log_with_timestamp(f"[DEBUG] Connect response sent: {response}")

    def is_running(self):
        return self.running

    async def handle_captive_portal_detection(self, writer, server_ip):
        log_with_timestamp("[DEBUG] Handling captive portal detection request")
        content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Success</title>
            <meta http-equiv="refresh" content="0;url=http://{server_ip}/index.html">
        </head>
        <body>
            <p>Success</p>
        </body>
        </html>
        """
        response = f"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(content)}\r\n\r\n{content}"
        writer.write(response.encode())
        await writer.drain()
        log_with_timestamp("[DEBUG] Captive portal detection response sent")