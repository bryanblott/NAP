################################################################################
# This module defines a DNSServer class that implements a simple asynchronous 
# DNS server using Python's asyncio library. The server listens for DNS requests 
# on port 53 and responds with a predefined IP address. It handles incoming DNS 
# requests concurrently and ensures controlled access to the DNS handling logic 
# using an asyncio.Lock.
#
# Classes:
#     DNSServer: A class to create and run an asynchronous DNS server.
#
# Usage:
#     Create an instance of the DNSServer class and call its run method within 
#     an asyncio event loop to start the server.
################################################################################


################################################################################
# Dependencies
################################################################################
import socket
import uasyncio as asyncio
from logging_utility import log


################################################################################
# DNS Query Class
################################################################################
class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ''
        self.parse_domain()

    def parse_domain(self):
        """Parse the domain name from the DNS query"""
        state = 0
        expected_length = 0
        domain_parts = []
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

    def response(self, ip):
        """Generate a response for the given IP address"""
        packet = self.data[:2] + b'\x81\x80'
        packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'  # Questions and Answers Counts
        packet += self.data[12:]  # Original Domain Name Question
        packet += b'\xc0\x0c'  # Pointer to domain name
        packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'  # Response type, ttl and resource data length -> 4 bytes
        packet += bytes(map(int, ip.split('.')))  # 4 bytes of IP
        return packet


################################################################################
# DNS Server Class
################################################################################
class DNSServer:
    def __init__(self, server_ip="192.168.4.1"):
        self.server_ip = server_ip
        self.udps = None
        self.lock = asyncio.Lock()  # Lock for concurrent DNS access

    async def run(self):
        """Run the DNS server to handle incoming DNS requests"""
        self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udps.setblocking(False)  # Set the socket to non-blocking mode
        try:
            self.udps.bind(('0.0.0.0', 53))
            log("DNS server started on port 53")

            while True:
                try:
                    await self.handle_dns(self.udps)
                except asyncio.CancelledError:
                    log("DNS server task cancelled, shutting down...", "WARNING")
                    break
                except Exception as e:
                    log(f"Error handling DNS query: {e}", "ERROR")
                    await asyncio.sleep(1)
        except OSError as e:
            log(f"Failed to bind DNS server on port 53: {e}", "ERROR")
            raise
        finally:
            if self.udps:
                log("Closing DNS server socket...")
                self.udps.close()  # Ensure socket is closed to release resources
                log("DNS server socket closed.")

    async def handle_dns(self, sock):
        """Handle DNS requests with a polling approach and controlled access"""
        async with self.lock:
            try:
                # Try receiving data from the socket, non-blocking
                data, addr = sock.recvfrom(4096)
                DNS = DNSQuery(data)
                log(f"Received DNS query for domain: {DNS.domain}")
                sock.sendto(DNS.response(self.server_ip), addr)
                log(f"Replying: {DNS.domain} -> {self.server_ip}")
            except asyncio.CancelledError:
                log("DNS handling task cancelled gracefully.", "WARNING")
            except OSError as e:
                if e.args[0] == 11:  # EAGAIN or no data received yet
                    await asyncio.sleep(0)  # Yield control back to the event loop
                else:
                    log(f"Unexpected error in DNS handling: {e}", "ERROR")
                    raise
            except Exception as e:
                log(f"General error in DNS handling: {e}", "ERROR")
                await asyncio.sleep(1)
