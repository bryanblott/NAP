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
import uasyncio as asyncio # type: ignore
from logging_utility import log


################################################################################
# Code
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
        try:
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
        except Exception as e:
            log(f"Error parsing domain: {e}", "ERROR")
            self.domain = ''  # Reset domain in case of error

    def response(self, ip):
        """Generate a response for the given IP address"""
        try:
            packet = self.data[:2] + b'\x81\x80'
            packet += self.data[4:6] + self.data[4:6] + b'\x00\x00\x00\x00'  # Questions and Answers Counts
            packet += self.data[12:]  # Original Domain Name Question
            packet += b'\xc0\x0c'  # Pointer to domain name
            packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'  # Response type, ttl and resource data length -> 4 bytes
            packet += bytes(map(int, ip.split('.')))  # 4 bytes of IP

            return packet
        except Exception as e:
            log(f"Error creating DNS response: {e}", "ERROR")
            return b''  # Return empty response in case of error


class DNSServer:
    def __init__(self, server_ip="192.168.4.1"):
        self.server_ip = server_ip
        self.udps = None
        self._running = False
        self.lock = asyncio.Lock()

    async def run(self):
        """Run the DNS server to handle incoming DNS requests"""
        await self.start()

    async def start(self):
        """Start the DNS server to handle incoming DNS requests"""
        self._running = True
        self.udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udps.setblocking(False)
        try:
            self.udps.bind(('0.0.0.0', 53))
            log("DNS server started on port 53")
            
            while self._running:
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
            await self.stop_internal()

    async def handle_dns(self, sock):
        """Handle DNS requests with a polling approach and controlled access"""
        async with self.lock:
            try:
                data, addr = sock.recvfrom(4096)
                if not data:
                    return

                DNS = DNSQuery(data)
                log(f"Received DNS query for domain: {DNS.domain}")

                if DNS.domain:
                    sock.sendto(DNS.response(self.server_ip), addr)
                    log(f"Replying: {DNS.domain} -> {self.server_ip}")
                else:
                    log("Invalid or empty domain received, ignoring...", "WARNING")

            except asyncio.CancelledError:
                await asyncio.sleep(0)
                return
            except OSError as e:
                if e.args[0] == 11:  # EAGAIN or no data received yet
                    await asyncio.sleep(0)
                else:
                    log(f"Unexpected error in DNS handling: {e}", "ERROR")
                    raise
            except Exception as e:
                log(f"General error in DNS handling: {e}", "ERROR")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the DNS server and release resources"""
        log("Stopping DNS server internal loop...")
        self._running = False
        if self.udps:
            log("Closing DNS server socket...")
            self.udps.close()
            self.udps = None
            log("DNS server socket closed.")
        await asyncio.sleep(0.1)

    async def stop_internal(self):
        """Internal stop method for cleanup and graceful shutdown"""
        if self.udps:
            log("Closing DNS server socket from internal stop...")
            self.udps.close()
            self.udps = None
            log("DNS server socket closed from internal stop.")
        log("DNS server internal loop stopped.")
