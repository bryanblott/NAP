from microdot import Microdot
import uasyncio as asyncio

# Define a simple Microdot application with debug enabled
app = Microdot(debug=True)

@app.route('/')
async def index(request):
    return 'Hello from Microdot!'

async def start_microdot_server():
    print("Starting Microdot server on port 8080 with debug enabled...")
    await app.start_server(host="0.0.0.0", port=8080)
    print("Microdot server started.")

asyncio.run(start_microdot_server())
