import uasyncio as asyncio
from captive_portal import CaptivePortal

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)

try:
    # Instantiate Portal and run
    portal = CaptivePortal()

    print("Starting event loop...")
    if IS_UASYNCIO_V3:
        asyncio.run(portal.start())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(portal.start())

except Exception as e:
    print(f'An exception occurred: {e}')

except KeyboardInterrupt:
    print('Bye')

finally:
    if IS_UASYNCIO_V3:
        asyncio.run(portal.http_server.close_server())  # Ensure HTTP server is closed
        asyncio.new_event_loop()  # Clear retained state