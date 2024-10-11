document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scanBtn');
    const networkSelect = document.getElementById('networks');
    const passwordInput = document.getElementById('password');
    const connectBtn = document.getElementById('connectBtn');
    const statusDiv = document.getElementById('status');

    scanBtn.addEventListener('click', fetchNetworks);
    connectBtn.addEventListener('click', connectToWiFi);

    function fetchNetworks() {
        statusDiv.textContent = 'Scanning for networks...';
        scanBtn.disabled = true;
        fetch('/scan')
            .then(response => {
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);
                return response.text().then(text => {
                    console.log('Response text:', text);
                    if (!response.ok) {
                        throw new Error(`Network response was not ok: ${text}`);
                    }
                    return JSON.parse(text);
                });
            })
            .then(data => {
                console.log('Parsed data:', data);
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
            })
            .catch(error => {
                console.error('Error fetching networks:', error);
                statusDiv.textContent = 'Failed to fetch networks: ' + error.message;
            })
            .finally(() => {
                scanBtn.disabled = false;
            });
    }

    function connectToWiFi() {
        const ssid = networkSelect.value;
        const password = passwordInput.value;
        
        if (!ssid) {
            statusDiv.textContent = 'Please select a network';
            return;
        }

        statusDiv.textContent = 'Connecting...';
        connectBtn.disabled = true;
        
        fetch('/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `ssid=${encodeURIComponent(ssid)}&password=${encodeURIComponent(password)}`
        })
        .then(response => response.text())
        .then(result => {
            statusDiv.textContent = result;
        })
        .catch(error => {
            console.error('Error:', error);
            statusDiv.textContent = 'Connection failed: ' + error.message;
        })
        .finally(() => {
            connectBtn.disabled = false;
        });
    }
});