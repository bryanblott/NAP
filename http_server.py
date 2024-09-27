import uasyncio as asyncio
import gc

class HTTPServer:
    def __init__(self, index_file='index.html'):
        self.index_file = index_file
        self.server = None  # Keep a reference to the server

    async def handle_connection(self, reader, writer):
        gc.collect()
        print("Handling HTTP request")

        # Basic response (no file handling for now)
        response = 'HTTP/1.0 200 OK\r\n\r\n'
        response += "<html><body><h1>ESP32 Captive Portal - Test Response</h1></body></html>"

        await writer.awrite(response)
        await writer.aclose()

    async def start(self):
        """Start the HTTP server on port 80 after a brief delay to ensure the network is ready."""
        await asyncio.sleep(3)  # Wait for Wi-Fi to fully initialize

        if self.server:
            print("Closing existing HTTP server instance before starting a new one.")
            await self.close_server()  # Close existing server before starting a new one

        try:
            print("Attempting to start HTTP server on port 80...")
            self.server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 80)
            print("HTTP server successfully started on port 80.")
        except OSError as e:
            print(f"Error starting HTTP server on port 80: {e}. Trying port 8080...")
            try:
                self.server = await asyncio.start_server(self.handle_connection, "0.0.0.0", 8080)
                print("HTTP server started on port 8080.")
            except OSError as e2:
                print(f"Error starting HTTP server on port 8080: {e2}")
                raise e2

    async def close_server(self):
        """Gracefully close the HTTP server if it exists."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("HTTP server closed successfully.")
            self.server = None