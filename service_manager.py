
################################################################################
# service_manager.py
#
# This module defines a ServiceManager class that manages the lifecycle of 
# various services such as the Wi-Fi access point, DNS server, and HTTP server.
# It provides methods to start and stop these services.
################################################################################

import uasyncio as asyncio
from logging_utility import create_logger

class ServiceManager:
    """A class to manage start and stop operations for multiple services."""

    def __init__(self, services):
        """Initialize the ServiceManager with a list of services."""
        self.services = services

    async def start_all(self):
        """Start all services asynchronously."""
        create_logger.info("Starting all services...")
        await asyncio.gather(*(service.start() for service in self.services))
        create_logger.info("All services started successfully.")

    async def stop_all(self):
        """Stop all services asynchronously."""
        create_logger.info("Stopping all services...")
        await asyncio.gather(*(service.stop() for service in self.services))
        create_logger.info("All services stopped successfully.")
