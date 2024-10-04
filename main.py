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
# main.py

import uasyncio as asyncio
from configuration import Configuration
from captive_portal import CaptivePortal
from wifi_client import WiFiClient
from http_server import HTTPServer
from logging_utility import create_logger

# Setup logging using the new Logger class
logger = create_logger("Main")

# Print the type of the logger to confirm it's an instance of the Logger class
print(f"Logger Type after initialization: {type(logger)}")  # Should print <class 'logging_utility.Logger'>

# Global variables to hold instances of CaptivePortal, WiFiClient, and HTTPServer
captive_portal_instance = None
wifi_client_instance = None
http_server_instance = None

async def start_captive_portal():
    """Start the captive portal and keep it running."""
    global captive_portal_instance, wifi_client_instance, http_server_instance

    logger.info("Loading configuration...")
    config = Configuration()  # Create a configuration object
    config.load()  # Ensure the configuration is loaded properly
    logger.info("Configuration loaded successfully.")

    # Access configuration data through config.config
    ssid = config.get("ssid")
    password = config.get("password")
    server_ip = config.get("server_ip")

    logger.info(f"Configuration values: SSID={ssid}, Password={password}, Server IP={server_ip}")

    # Create and start the Captive Portal
    logger.info("Creating Captive Portal instance...")
    captive_portal_instance = CaptivePortal(config.config)  # Pass config.config, not config itself
    await captive_portal_instance.start()
    logger.info("Captive Portal started successfully.")

    # Create a WiFi Client instance
    logger.info("Creating WiFiClient instance...")
    wifi_client_instance = WiFiClient()
    logger.info("WiFiClient instance created successfully.")

    # Create an HTTP Server instance with the WiFiClient instance
    logger.info("Creating HTTPServer instance with WiFiClient...")
    http_server_instance = HTTPServer("0.0.0.0", 80, wifi_client_instance)
    logger.info("HTTPServer instance created successfully.")

    # Ensure the HTTP server starts
    await http_server_instance.start()

async def shutdown_captive_portal():
    """Gracefully shutdown the Captive Portal and related services."""
    global captive_portal_instance, wifi_client_instance, http_server_instance

    logger.info("Shutting down Captive Portal...")

    if http_server_instance:
        logger.info("Stopping HTTP Server...")
        await http_server_instance.stop()
        logger.info("HTTP Server stopped.")

    if captive_portal_instance:
        logger.info("Stopping Captive Portal...")
        await captive_portal_instance.stop()
        logger.info("Captive Portal stopped.")

    # Reset global variables
    captive_portal_instance = None
    wifi_client_instance = None
    http_server_instance = None

    logger.info("Captive Portal shutdown completed successfully.")

async def main():
    """Main function to run and later shut down the captive portal."""
    try:
        await start_captive_portal()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await shutdown_captive_portal()
        logger.info("Event loop closed.")

# Run the main function using asyncio
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted manually.")
        loop.run_until_complete(shutdown_captive_portal())
    finally:
        loop.close()
        logger.info("Application terminated.")
