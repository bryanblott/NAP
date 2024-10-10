// script.js

// Fetch the list of available Wi-Fi networks and populate the dropdown
function fetchNetworks() {
    document.getElementById('status').textContent = 'Scanning for networks...';
    fetch('/scan')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            if (data.trim() === '') {
                throw new Error('No networks found');
            }
            const networks = data.split(',').filter(network => network.trim() !== '');
            const networkSelect = document.getElementById('networks');
            networkSelect.innerHTML = ''; // Clear existing options
            networks.forEach(network => {
                const option = document.createElement('option');
                option.value = network;
                option.textContent = network;
                networkSelect.appendChild(option);
            });
            console.log('Networks loaded:', networks);
            document.getElementById('status').textContent = `Found ${networks.length} networks`;
        })
        .catch(error => {
            console.error('Error fetching networks:', error);
            document.getElementById('status').textContent = 'Failed to fetch networks: ' + error.message;
        });
}

function connectToWiFi() {
    const ssid = document.getElementById('networks').value;
    const password = document.getElementById('password').value;
    
    if (!ssid) {
        document.getElementById('status').textContent = 'Please select a network';
        return;
    }

    document.getElementById('status').textContent = 'Connecting...';
    
    fetch('/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `ssid=${encodeURIComponent(ssid)}&password=${encodeURIComponent(password)}`
    })
    .then(response => response.text())
    .then(result => {
        document.getElementById('status').textContent = result;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('status').textContent = 'Connection failed: ' + error.message;
    });
}

// Add event listeners when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Fetch networks after a short delay to ensure backend is ready
    setTimeout(fetchNetworks, 1000);

    // Add click event for connect button
    document.getElementById('connectBtn').addEventListener('click', connectToWiFi);

    // Add click event for refresh button (if you have one)
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchNetworks);
    }
});
