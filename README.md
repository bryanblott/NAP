# NAP - Not Another Portal!
## ESP32 Captive Portal with DNS and HTTP Server

NAP is a project that creates a captive portal on an ESP32 device using MicroPython. It sets up a Wi-Fi access point, a DNS server, and an HTTP server with optional TLS support. 

NAP was born out of my personal frustration with many of the captive portal libraries that I have played with in the past, and the difficulty I have had while trying to implement other microcontroller functionality alonside them. It is designed in such a way that major functionality has been moved to classes that can easily be refactored, augmented, or replaced. Adding new classes without breaking existing functionality should be reliatively simple as well.

Currently this project has been incompletely tested on ESP32 devices only. 

## Coming Soon:

- A better default HTML interface
- Functionality to join your ESP32 existing WiFi networks and turn off AP mode
- GPIO examples, including a reset button
- TLS/SSL/HTTPS examples and documentation
- Moving more functionality to config.json 

## Project Overview

### Features
- **Wi-Fi Access Point:** Creates a Wi-Fi access point (AP) with customizable SSID and password, enabling devices to connect directly to the ESP32.
- **DNS Server:** Handles DNS requests and resolves all domains to the IP address of the ESP32. This behavior is typical for captive portals, as it ensures all requests from connected clients are redirected to the HTTP server.
- **HTTP Server with Optional TLS Support:** Serves a configurable `index.html` file or a default HTML page. Supports both HTTP and HTTPS (if certificate and key files are provided).
- **Configuration Management:** Uses a configuration file (`config.json`) to store and manage settings such as the SSID, password, and server IP address. If the file is not found, it will create a default configuration.
- **Watchdog Timer:** Utilizes the ESP32's built-in watchdog timer to reset the device if it hangs or crashes, ensuring reliability and stability.
- **Graceful Shutdown:** Listens for keyboard interrupts and gracefully shuts down all services when stopping the portal.

## Directory Structure
```
/project_root
    ├── main.py              # Entry point for the program
    ├── configuration.py     # Configuration management class
    ├── wifi_access_point.py # Wi-Fi Access Point class
    ├── dns_server.py        # DNS Server and DNSQuery classes
    ├── http_server.py       # HTTPServer class
    ├── captive_portal.py    # CaptivePortal class to coordinate the servers
    ├── logging_utility.py   # Utility module containing the log function
    └── config.json          # Configuration file (created if not found)
```

## Prerequisites
1. **MicroPython 1.23.0 or later**: The project is built specifically for MicroPython 1.23.0+ as it uses the `tls` library for SSL/TLS support, which is available in this version and later.
2. **ESP32 Board**: This project targets the ESP32 microcontroller, which is ideal for Wi-Fi and network-related applications.
3. **MicroPython Libraries**: Make sure to have `uasyncio`, `network`, `socket`, `gc`, `time`, `machine`, `json`, `os`, and `tls` modules available on your ESP32.

## Setup and Usage

1. **Clone or Download the Repository:**

   Clone the repository or download the project files to your development environment.

2. **Upload Files to ESP32:**

   Use a tool like [ampy](https://github.com/scientifichackers/ampy) or [mpfshell](https://github.com/wendlers/mpfshell) to upload the `.py` files and `config.json` to your ESP32.

   ```bash
   ampy --port /dev/ttyUSB0 put main.py
   ampy --port /dev/ttyUSB0 put configuration.py
   ampy --port /dev/ttyUSB0 put wifi_access_point.py
   ampy --port /dev/ttyUSB0 put dns_server.py
   ampy --port /dev/ttyUSB0 put http_server.py
   ampy --port /dev/ttyUSB0 put captive_portal.py
   ampy --port /dev/ttyUSB0 put logging_utility.py
   ```

3. **Create a Configuration File:**

   If the `config.json` file is not present, the program will automatically create it with default values. You can also create this file manually with the following content:

   ```json
   {
     "ssid": "ESP32_Captive_Portal",
     "password": "12345678",
     "server_ip": "192.168.4.1"
   }
   ```

4. **Run the Program:**

   Run the `main.py` file from your ESP32.

   ```bash
   ampy --port /dev/ttyUSB0 run main.py
   ```

   Or connect to the device using a serial console (e.g., `screen`, `minicom`, or `picocom`) and execute `main.py`.

5. **Connect to the Wi-Fi Access Point:**

   Find the SSID specified in the configuration file (default is `ESP32_Captive_Portal`) and connect using the password provided.

6. **Access the Captive Portal:**

   Open any web browser on the connected device and try to access any webpage. You will be redirected to the captive portal served by the ESP32.

## Customization

### Adding Custom HTML Content
If you want to display a custom HTML page, upload your `index.html` file to the ESP32. The HTTP server will prioritize serving this file over the default HTML content.

### Enabling HTTPS
If you want to enable HTTPS, upload your `cert.pem` and `private.key` files to the ESP32. The HTTP server will automatically switch to HTTPS if these files are found.

## Troubleshooting

- **DNS Server Not Responding:**
  Check if the DNS server is correctly bound to port 53 and that no other service is using this port.

- **TLS/SSL Errors:**
  Make sure the `cert.pem` and `private.key` files are correctly formatted and accessible by the ESP32.

- **Watchdog Timer Resets:**
  If you encounter frequent watchdog resets, consider increasing the watchdog timer timeout value or investigating potential blocking code within the main loop.

## Limitations
- This project is specifically built for ESP32 with MicroPython and may not work on other microcontrollers or MicroPython implementations without modification.
- TLS/SSL support requires sufficient memory and might not work on all ESP32 variants with lower memory configurations.

## License
This project is open-source and distributed under the MIT License. Feel free to use, modify, and distribute it as per the terms of the license.

## Acknowledgements
Special thanks to the [MicroPython](https://micropython.org/) community for developing such a powerful tool for microcontroller programming!
