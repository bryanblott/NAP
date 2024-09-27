from microdot import Microdot, Response
import gc
import uasyncio as asyncio

class HTTPServer:
    def __init__(self, index_file='index.html'):
        self.index_file = index_file
        self.app = Microdot()
        Response.default_content_type = 'text/html'

        @self.app.route('/')
        def index(request):
            gc.collect()
            return "<html><body><h1>ESP32 Captive Portal - Test Response</h1></body></html>"

    async def start(self):
        """Start the HTTP server on port 80 after a brief delay to ensure the network is ready."""
        await asyncio.sleep(3)  # Wait for Wi-Fi to fully initialize

        if self.app:
            print("Closing existing HTTP server instance before starting a new one.")
            await self.close_server()  # Close existing server before starting a new one

        try:
            print("Attempting to start HTTP server on port 80...")
            self.app.run(host='0.0.0.0', port=80)
            print("HTTP server successfully started on port 80.")
        except OSError as e:
            print(f"Error starting HTTP server on port 80: {e}. Trying port 8080...")
            try:
                self.app.run(host='0.0.0.0', port=8080)
                print("HTTP server started on port 8080.")
            except OSError as e2:
                print(f"Error starting HTTP server on port 8080: {e2}")
                raise e2

    async def close_server(self):
        """Gracefully close the HTTP server if it exists."""
        if self.app:
            print("Attempting to shut down HTTP server...")
            try:
                self.app.shutdown()
                print("HTTP server closed successfully.")
            except Exception as e:
                print(f"Error shutting down HTTP server: {e}")
            finally:
                self.app = None