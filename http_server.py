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
        if self.use_tls:
            context = tls.SSLContext(tls.PROTOCOL_TLS_SERVER)
            try:
                context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
            except Exception as e:
                print(f"[ERROR] Failed to load TLS cert/key: {e}")
                print("[WARNING] Falling back to HTTP")
                self.use_tls = False

        try:
            if self.use_tls:
                self.server = await asyncio.start_server(self.handle_request, self.host, self.port, ssl=context)
                print(f"[INFO] HTTPS Server: Started on {self.host}:{self.port}")
            else:
                self.server = await asyncio.start_server(self.handle_request, self.host, self.port)
                print(f"[INFO] HTTP Server: Started on {self.host}:{self.port}")

            self.running = True
            while self.running:
                try:
                    await asyncio.sleep(1)  # Allow for cancellation
                except asyncio.CancelledError:
                    print("[INFO] HTTP(S) Server: Received cancellation signal")
                    break
        except Exception as e:
            print(f"[ERROR] HTTP(S) Server: Failed to start: {e}")
        finally:
            await self.stop()

    async def stop(self):
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print("[INFO] HTTP(S) Server: Stopped")

    async def handle_request(self, reader, writer):
        try:
            request_line = await reader.readline()
            print(f"[DEBUG] HTTP(S) Server: Received request: {request_line}")
            
            # Parse the request
            method, path, _ = request_line.decode().strip().split(' ', 2)
            
            if path == '/' or not path.startswith('/index.html'):
                # Redirect to the captive portal page
                response = "HTTP/1.0 302 Found\r\nLocation: /index.html\r\n\r\n"
                writer.write(response.encode('utf-8'))
            else:
                # Serve the requested file
                await self.serve_file(path.lstrip('/'), writer)
            
            await writer.drain()
        except Exception as e:
            print(f"[ERROR] HTTP(S) Server: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def serve_file(self, path, writer):
        try:
            with open(f"{self.root_directory}/{path}", "rb") as file:
                writer.write(b"HTTP/1.0 200 OK\r\n")
                if path.endswith('.html'):
                    writer.write(b"Content-Type: text/html\r\n\r\n")
                elif path.endswith('.css'):
                    writer.write(b"Content-Type: text/css\r\n\r\n")
                elif path.endswith('.js'):
                    writer.write(b"Content-Type: application/javascript\r\n\r\n")
                else:
                    writer.write(b"Content-Type: text/plain\r\n\r\n")
                
                chunk = file.read(1024)
                while chunk:
                    writer.write(chunk)
                    await writer.drain()
                    chunk = file.read(1024)
        except OSError:
            response = "HTTP/1.0 404 Not Found\r\n\r\nFile not found"
            writer.write(response.encode('utf-8'))
            await writer.drain()

# Example usage:
# server = HTTPServer(root_directory='www', host='0.0.0.0', port=80, ssl_certfile='cert.pem', ssl_keyfile='private.key')
# asyncio.run(server.start())