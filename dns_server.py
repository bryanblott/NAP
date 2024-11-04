import socket
import uasyncio as asyncio
from utils import log_with_timestamp  # Updated import

class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        self.parse_domain()

    def parse_domain(self):
        kind = (self.data[2] >> 3) & 15
        if kind == 0:
            ini = 12
            lon = self.data[ini]
            while lon != 0:
                self.domain += self.data[ini+1:ini+lon+1].decode('utf-8') + '.'
                ini += lon + 1
                lon = self.data[ini]
        log_with_timestamp(f"[DEBUG] DNSQuery: Parsed domain: {self.domain}")

    def response(self, ip):
        packet = self.data[:2] + b'\x81\x80'
        packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'
        packet += self.data[12:]
        packet += b'\xc0\x0c'
        packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'
        packet += bytes(map(int, ip.split('.')))
        return packet

class DNSServer:
    def __init__(self, ip):
        self.ip = ip
        self.socket = None
        self.running = False

    async def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind(('0.0.0.0', 53))
            log_with_timestamp("[INFO] DNS Server: Started on port 53")
            self.running = True
            while self.running:
                try:
                    yield asyncio.core._io_queue.queue_read(self.socket)
                    data, addr = self.socket.recvfrom(512)
                    if data:
                        log_with_timestamp(f"[DEBUG] DNS Server: Received request from {addr}")
                        request = DNSQuery(data)
                        response = request.response(self.ip)
                        self.socket.sendto(response, addr)
                        log_with_timestamp(f"[INFO] DNS Server: Responded {request.domain} -> {self.ip}")
                    await asyncio.sleep_ms(1)  # Cooperative yield
                except asyncio.CancelledError:
                    log_with_timestamp("[INFO] DNS Server: Received cancellation signal")
                    break
                except Exception as e:
                    log_with_timestamp(f"[ERROR] DNS Server: {e}")
                await asyncio.sleep_ms(1)  # Cooperative yield
        except Exception as e:
            log_with_timestamp(f"[ERROR] DNS Server: Failed to start: {e}")
        finally:
            await self.stop()

    async def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                log_with_timestamp(f"[ERROR] DNS Server: Error closing socket: {e}")
        log_with_timestamp("[INFO] DNS Server: Stopped")