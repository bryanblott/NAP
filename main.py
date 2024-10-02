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
import machine  # Import machine module to use reset functionality
from configuration import Configuration
from captive_portal import CaptivePortal
from logging_utility import log

################################################################################
# Main Execution
################################################################################

# Global flag to ensure graceful shutdown
shutdown_flag = False

# Main application entry point
async def main():
    global shutdown_flag
    shutdown_flag = False  # Reset shutdown flag

    # Load configuration
    config = Configuration()
    config.load()

    # Create and start the captive portal
    portal = CaptivePortal(config.config)
    await portal.start()

async def shutdown(loop, portal):
    """Handle shutdown process for all tasks and event loop."""
    global shutdown_flag

    # Prevent multiple shutdown calls
    if shutdown_flag:
        log("Shutdown already in progress. Ignoring additional shutdown requests.", "WARNING")
        return

    shutdown_flag = True  # Set shutdown flag

    log("Stopping Captive Portal...")
    # Signal the portal to stop and await its completion
    await portal.stop()

    log("Closing event loop and cancelling all tasks...")

    # Stop the event loop if it's still running
    if loop:
        loop.stop()  # Stop the loop to ensure no more tasks are scheduled
        log("Event loop stopped.")

    log("Event loop closed successfully.")

try:
    log("Starting event loop...")
    loop = asyncio.get_event_loop()
    portal = None

    # Instantiate CaptivePortal globally to access during shutdown
    config = Configuration()
    config.load()
    portal = CaptivePortal(config.config)

    # Run the main function until complete
    loop.run_until_complete(main())
except KeyboardInterrupt:
    log('Keyboard Interrupt detected. Shutting down...', "WARNING")
    if portal:
        loop.run_until_complete(shutdown(loop, portal))
finally:
    # Final cleanup
    if portal:
        log("Final cleanup: Stopping the Captive Portal if not already stopped.")
        loop.run_until_complete(portal.stop())

    log("Application shutdown completed.")

    # Reboot the ESP32 as the final cleanup action
    log("Rebooting the ESP32 to complete the shutdown process...", "INFO")
    machine.reset()  # Perform a hard reset to reboot the ESP32
