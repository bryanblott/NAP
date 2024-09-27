import socket
import uasyncio as asyncio
from dns_query import DNSQuery

class DNSServer:
    def __init__(self, server_ip="192.168.4.1"):
        self.server_ip = server_ip

    async def run(self):
        """Run the DNS server to handle incoming DNS requests"""
        udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udps.setblocking(False)  # Set the socket to non-blocking mode
        udps.bind(('0.0.0.0', 53))

        print("DNS server started on port 53")

        while True:
            try:
                await self.handle_dns(udps)
            except Exception as e:
                print(f"Error handling DNS query: {e}")
                await asyncio.sleep(1)

        udps.close()

    async def handle_dns(self, sock):
        """Handle DNS requests with a polling approach"""
        try:
            # Try receiving data from the socket, non-blocking
            data, addr = sock.recvfrom(4096)
            DNS = DNSQuery(data)
            print(f"Received DNS query for domain: {DNS.domain}")
            sock.sendto(DNS.response(self.server_ip), addr)
            print(f"Replying: {DNS.domain} -> {self.server_ip}")
        except OSError as e:
            if e.args[0] == 11:  # EAGAIN or no data received yet
                await asyncio.sleep(0)  # Yield control back to the event loop
            else:
                raise