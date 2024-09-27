# PS200

Prep:

1. Install esptool

```
pip3 install esptool
```

2. Download the MicroPython Firmware
- Go to the MicroPython Download Page for ESP32. https://micropython.org/download/#esp32
- Download the appropriate .bin file for your ESP32 board (usually the latest stable release is a good choice).


bryanblott@SkylarkMBP-2 ~ % echo $PATH
/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/opt/X11/bin:/Library/Apple/usr/bin:/usr/local/go/bin

export PATH="$PATH:/Users/bryanblott/Library/Python/3.9/bin"

Serial port /dev/cu.usbserial-0001

3. ESP32_GENERIC-20240602-v1.23.0

esptool.py --chip esp32 --port /dev/cu.usbserial-0001 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20240602-v1.23.0.bin

4. based

python3 -m serial.tools.miniterm /dev/cu.usbserial-0001 115200





Default PyMaker JSON for device configs:

```
{
    "pymakr.devices.configs": {

        "serial:///dev/tty.BLTH": {
            "autoConnect": "onLostConnection",
            "name": "",
            "username": "micro",
            "password": "python",
            "hidden": false,
            "rootPath": null,
            "adapterOptions": {}
        },
        "0001": {
            "autoConnect": "onLostConnection",
            "name": "",
            "username": "micro",
            "password": "python",
            "hidden": false,
            "rootPath": "/",
            "adapterOptions": {}
        },
        "serial:///dev/tty.Bluetooth-Incoming-Port": {
            "autoConnect": "onLostConnection",
            "name": "",
            "username": "micro",
            "password": "python",
            "hidden": false,
            "rootPath": null,
            "adapterOptions": {}
        }
    },
    "pymakr.devices.include": [
        "manufacturer=Pycom.*",
        "manufacturer=FTDI",
        "manufacturer=Microsoft",
        "manufacturer=Microchip Technology.*",
        "friendlyName=.*CH34[01].*",
        "friendlyName=.*CP21.*",
        "manufacturer=(?!undefined)",
        "manufacturer=Silicon Laboratories*",
        "manufacturer=Silicon Labs*"
    ],
    "pymakr.devices.nameTemplate": "{displayName} / {productId} / {projectName}",
    "explorer.confirmPasteNative": false,
    "workbench.activityBar.location": "top"
}
```
