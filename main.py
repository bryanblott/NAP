###############################################################################
# This script initializes and runs a captive portal using uasyncio for 
# asynchronous operations. It loads the configuration, detects the version of 
# uasyncio, and starts the event loop accordingly. The script ensures proper 
# handling of exceptions and keyboard interrupts, and it guarantees that all 
# servers are closed upon termination.
#
# Dependencies:
# - uasyncio (as asyncio)
# - Configuration (from configuration module)
# - CaptivePortal (from captive_portal module)
#
# Attributes:
# - IS_UASYNCIO_V3 (bool): A flag indicating if the uasyncio version is 3 or 
#   higher.
#
# Usage:
# - Load configuration using the Configuration class.
# - Instantiate the CaptivePortal with the loaded configuration.
# - Start the event loop using asyncio.run() for uasyncio v3 or get_event_loop() 
#   for earlier versions.
# - Handle exceptions and keyboard interrupts gracefully.
# - Ensure all servers are closed in the finally block.
###############################################################################


################################################################################
# Dependencies
################################################################################
import uasyncio as asyncio
from configuration import Configuration
from captive_portal import CaptivePortal


################################################################################
# Code
################################################################################

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
