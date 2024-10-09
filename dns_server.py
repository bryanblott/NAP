# Adding additional debug logging to dns_server.py for better diagnosis

import socket
import uasyncio as asyncio
import time

class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        print(f"[DEBUG] Initializing DNSQuery with data: {data}")
        self.parse_domain()

    def parse_domain(self):
        """Parse the domain name from the DNS query"""
        state = 0
        expected_length = 0
        domain_parts = []
        print(f"[DEBUG] Parsing domain from DNS data: {self.data[12:]}")
        for byte in self.data[12:]:
            if state == 1:
                if byte == 0:
                    break
                domain_parts.append(chr(byte))
                expected_length -= 1
                if expected_length == 0:
                    domain_parts.append('.')
                    state = 0
            else:
                expected_length = byte
                if expected_length == 0:
                    break
                state = 1
        self.domain = ''.join(domain_parts).strip('.')
        print(f"[INFO] Parsed domain: {self.domain}")

    def response(self, ip):
        """Generate a response for the given IP address"""
        try:
            packet = self.data[:2] + b'\x81\x80'
            packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'  # Questions and Answers Counts
            packet += self.data[12:]  # Original Domain Name Question
            packet += b'\xc0\x0c'  # Pointer to domain name
            packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'  # Response type, ttl and resource data length -> 4 bytes
            packet += bytes(map(int, ip.split('.')))  # 4 bytes of IP
            print(f"[INFO] Generated DNS response for {ip}")
            return packet
        except Exception as e:
            print(f"[ERROR] Error creating DNS response: {e}")
            return b''  # Return empty response in case of error


class DNSServer:
    def __init__(self, server_ip="192.168.4.1"):
        self.server_ip = server_ip
        self.udps = None
        self._running = False
        self.lock = asyncio.Lock()
        self.last_status_update = 0
        print(f"[INFO] DNSServer initialized with IP: {self.server_ip}")

    async def start(self):
        """Start the DNS server to handle incoming DNS requests"""
        self._running = True
        self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udps.setblocking(False)
        try:
            self.udps.bind(('0.0.0.0', 53))
            print("[INFO] DNS server started on port 53")
            
            while self._running:
                try:
                    await self.handle_dns(self.udps)
                    await self.print_status_update()
                except asyncio.CancelledError:
                    print("[WARNING] DNS server task cancelled, shutting down...")
                    break
                except Exception as e:
                    print(f"[ERROR] Error in DNS server main loop: {e}")
                    await asyncio.sleep(1)
        except OSError as e:
            print(f"[ERROR] Failed to bind DNS server on port 53: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the DNS server and release resources"""
        print("[INFO] Stopping DNS server...")
        self._running = False
        if self.udps:
            self.udps.close()
            self.udps = None
        print("[INFO] DNS server stopped.")

    async def handle_dns(self, sock):
        """Handle DNS requests with a polling approach and controlled access"""
        async with self.lock:
            try:
                data, addr = sock.recvfrom(4096)
                if data:
                    print(f"[INFO] Received DNS request from {addr}")
                    DNS = DNSQuery(data)
                    response = DNS.response(self.server_ip)
                    sock.sendto(response, addr)
                    print(f"[INFO] Replied: {DNS.domain} -> {self.server_ip}")
            except OSError as e:
                if e.args[0] != 11:  # 11 is EAGAIN, meaning no data available
                    print(f"[ERROR] Unexpected error in DNS handling: {e}")
            await asyncio.sleep(0.1)

    async def print_status_update(self):
        """Print a status update every 60 seconds"""
        current_time = time.time()
        if current_time - self.last_status_update >= 60:
            print("[INFO] DNS Server is running and waiting for requests...")
            self.last_status_update = current_time