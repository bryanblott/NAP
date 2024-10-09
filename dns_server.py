import socket
import uasyncio as asyncio

class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        self.parse_domain()

    def parse_domain(self):
        kind = (self.data[2] >> 3) & 15   # Opcode bits
        if kind == 0:                     # Standard query
            ini = 12
            lon = self.data[ini]
            while lon != 0:
                self.domain += self.data[ini+1:ini+lon+1].decode('utf-8') + '.'
                ini += lon + 1
                lon = self.data[ini]
        print(f"[DEBUG] DNSQuery: Parsed domain: {self.domain}")

    def response(self, ip):
        packet = self.data[:2] + b'\x81\x80'
        packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'   # Questions and Answers Counts
        packet += self.data[12:]                                          # Original Domain Name Question
        packet += b'\xc0\x0c'                                             # Pointer to domain name
        packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
        packet += bytes(map(int, ip.split('.')))                          # 4 bytes of IP
        return packet

class DNSServer:
    def __init__(self, ip="192.168.4.1"):
        self.ip = ip
        self.socket = None
        self.running = False

    async def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind(('0.0.0.0', 53))
            print("[INFO] DNS Server: Started on port 53")
            self.running = True
            while self.running:
                try:
                    yield asyncio.core._io_queue.queue_read(self.socket)
                    data, addr = self.socket.recvfrom(512)
                    if data:
                        print(f"[DEBUG] DNS Server: Received request from {addr}")
                        request = DNSQuery(data)
                        response = request.response(self.ip)
                        self.socket.sendto(response, addr)
                        print(f"[INFO] DNS Server: Responded {request.domain} -> {self.ip}")
                except asyncio.CancelledError:
                    print("[INFO] DNS Server: Received cancellation signal")
                    break
                except Exception as e:
                    print(f"[ERROR] DNS Server: {e}")
        except Exception as e:
            print(f"[ERROR] DNS Server: Failed to start: {e}")
        finally:
            await self.stop()

    async def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"[ERROR] DNS Server: Error closing socket: {e}")
        print("[INFO] DNS Server: Stopped")