import network
import time
import uasyncio
from microdot import Microdot
from machine import Pin
import security
from security import WIFI_SSID
from security import WIFI_PASSWORD

# WIFI CONNECTION
# ssid = 'SOMEWIFINAME'
# password = 'SOMEWIFIPASSWORD'
ssid = WIFI_SSID
password = WIFI_PASSWORD
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
time.sleep(1.5)
wlan.connect(ssid, password)
print('Connecting')
while wlan.isconnected() == False and wlan.status() < 0:
    print(f".", end = "")
    time.sleep(1)
print("Connected! IP Address = " + wlan.ifconfig()[0])

# CONFIGURE SERVER
app = Microdot()
@app.route('/')
def index(request):
    return 'Hello, You!'

async def start_server():
    app.run(port=5000)

# ANOTHER STUFF YOU WANNA DO WHILE SERVER IS RUNNING
async def button_monitor():
    # JUST READING VALUE FROM A BUTTON
    button_pin = Pin(2, Pin.IN, Pin.PULL_DOWN)
    while True:
        if button_pin.value() == 1:         
            print("Button pressed!")
        await uasyncio.sleep(1)

# ASYNCIO MAGIC
async def main():
    uasyncio.create_task(start_server())
    uasyncio.create_task(button_monitor())
    while True:
        await uasyncio.sleep(100)
        