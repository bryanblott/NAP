# import pycom
# import time

# pycom.heartbeat(False)

# while True:
#     pycom.rgbled(0xFF0000)  # Red
#     time.sleep(1)
#     pycom.rgbled(0x00FF00)  # Green
#     time.sleep(1)
#     pycom.rgbled(0x0000FF)  # Blue
#     time.sleep(1)

# from machine import Pin
# from time import sleep

# led = Pin(23, Pin.OUT)

# while True:
#   led.value(not led.value())
#   sleep(1)

# ""
# Minimal captive portal, using uasyncio v3 (MicroPython 1.13+) with a fallback for earlier versions of uasyncio/MicroPython.

# * License: MIT
# * Repository: https://github.com/metachris/micropython-captiveportal
# * Author: Chris Hager <chris@linuxuser.at> / https://twitter.com/metachris

# Built upon:
# - https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal

# References:
# - http://docs.micropython.org/en/latest/library/uasyncio.html
# - https://github.com/peterhinch/micropython-async/blob/master/v3/README.md
# - https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md
# - https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5
# """
import gc
import sys
import network
import socket
import uasyncio as asyncio
import os
import portal
# import portal.portal
# from portal.portal import PS200Portal

# Helper to detect uasyncio v3
IS_UASYNCIO_V3 = hasattr(asyncio, "__version__") and asyncio.__version__ >= (3,)



# Main code entrypoint
try:
    # Instantiate app and run
    ps200Portal = PS200Portal()

    if IS_UASYNCIO_V3:
        asyncio.run(ps200Portal.start())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(ps200Portal.start())

except KeyboardInterrupt:
    print('Bye')

finally:
    if IS_UASYNCIO_V3:
        asyncio.new_event_loop()  # Clear retained state