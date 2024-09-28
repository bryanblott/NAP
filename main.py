# main.py
import uasyncio as asyncio
from configuration import Configuration
from captive_portal import CaptivePortal

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)

# Load configuration
config = Configuration()
config.load()

# Instantiate Portal and run
portal = CaptivePortal(config.config)

try:
    print("[INFO] Starting event loop...")
    if IS_UASYNCIO_V3:
        asyncio.run(portal.start())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(portal.start())

except Exception as e:
    print(f"[ERROR] An exception occurred: {e}")

except KeyboardInterrupt:
    print('[WARNING] Keyboard Interrupt detected. Shutting down...')

finally:
    if IS_UASYNCIO_V3:
        asyncio.run(portal.stop())  # Ensure all servers are closed
