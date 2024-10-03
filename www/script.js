
// script.js

// Fetch the list of available Wi-Fi networks and populate the dropdown
function fetchNetworks() {
    fetch('/scan').then(response => response.json()).then(networks => {
        const networkSelect = document.getElementById('networks');
        networks.forEach(network => {
            const option = document.createElement('option');
            option.value = network;
            option.textContent = network;
            networkSelect.appendChild(option);
        });
    }).catch(error => console.error('Error fetching networks:', error));
}

// Handle form submission to connect to a selected Wi-Fi network
function connectToWiFi() {
    const networkSelect = document.getElementById('networks');
    const passwordInput = document.getElementById('password');
    const ssid = networkSelect.value;
    const password = passwordInput.value;

    // Send a POST request to the server with SSID and password
    fetch('/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `ssid=${encodeURIComponent(ssid)}&password=${encodeURIComponent(password)}`
    }).then(response => response.text()).then(status => {
        document.getElementById('status').textContent = `Connection status: ${status}`;
    }).catch(error => console.error('Error connecting to Wi-Fi:', error));
}

// Fetch available networks when the page loads
document.addEventListener('DOMContentLoaded', fetchNetworks);
