document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scanBtn');
    const networkSelect = document.getElementById('networks');
    const passwordInput = document.getElementById('password');
    const connectBtn = document.getElementById('connectBtn');
    const statusDiv = document.getElementById('status');

    scanBtn.addEventListener('click', fetchNetworks);
    connectBtn.addEventListener('click', connectToWiFi);

    function logWithTimestamp(message) {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] ${message}`);
    }

    function fetchNetworks() {
        statusDiv.textContent = 'Scanning for networks...';
        scanBtn.disabled = true;
        logWithTimestamp('Initiating network scan');
        fetch('/scan')
            .then(response => {
                logWithTimestamp(`Scan response received. Status: ${response.status}`);
                return response.text().then(text => {
                    logWithTimestamp(`Response text: ${text}`);
                    if (!response.ok) {
                        throw new Error(`Network response was not ok: ${text}`);
                    }
                    return JSON.parse(text);
                });
            })
            .then(data => {
                logWithTimestamp(`Parsed scan data: ${JSON.stringify(data)}`);
                if (!data.networks || data.networks.length === 0) {
                    throw new Error('No networks found');
                }
                networkSelect.innerHTML = '<option value="">Select a network</option>';
                data.networks.forEach(network => {
                    const option = document.createElement('option');
                    option.value = network;
                    option.textContent = network;
                    networkSelect.appendChild(option);
                });
                statusDiv.textContent = `Found ${data.networks.length} networks`;
                logWithTimestamp(`Updated network list with ${data.networks.length} networks`);
            })
            .catch(error => {
                logWithTimestamp(`Error fetching networks: ${error.message}`);
                statusDiv.textContent = 'Failed to fetch networks: ' + error.message;
            })
            .finally(() => {
                scanBtn.disabled = false;
                logWithTimestamp('Network scan process completed');
            });
    }

    function connectToWiFi() {
        const ssid = networkSelect.value;
        const password = passwordInput.value;
        
        if (!ssid) {
            statusDiv.textContent = 'Please select a network';
            return;
        }
        
        statusDiv.textContent = `Connecting to ${ssid}...`;
        connectBtn.disabled = true;
        logWithTimestamp(`Initiating connection to SSID: ${ssid}`);
        
        fetch('/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `ssid=${encodeURIComponent(ssid)}&password=${encodeURIComponent(password)}`
        })
        .then(response => response.text())
        .then(result => {
            logWithTimestamp(`Connection result: ${result}`);
            statusDiv.innerHTML = result;  // Changed to innerHTML to support formatted text
            
            // If connection was successful, adjust status div styling
            if (result.includes('Connected successfully')) {
                statusDiv.style.color = '#00ff00';  // Green color for success
            } else {
                statusDiv.style.color = '#ff0000';  // Red color for failure
            }
        })
        .catch(error => {
            logWithTimestamp(`Connection error: ${error.message}`);
            statusDiv.textContent = 'Connection failed: ' + error.message;
            statusDiv.style.color = '#ff0000';  // Red color for error
        })
        .finally(() => {
            connectBtn.disabled = false;
            logWithTimestamp('Connection process completed');
        });
    }
});