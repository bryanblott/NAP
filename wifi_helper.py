
################################################################################
# wifi_helper.py
#
# This module provides helper functions for common Wi-Fi initialization and
# configuration tasks, which are shared between WiFiAccessPoint and WiFiClient.
################################################################################

from network import WLAN

def initialize_wifi_interface(interface_type):
    """Initialize a WLAN interface with the specified type."""
    wlan = WLAN(interface_type)
    wlan.active(True)
    return wlan
