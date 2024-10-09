
// script.js

// Fetch the list of available Wi-Fi networks and populate the dropdown
function fetchNetworks() {
    fetch('/scan')
        .then(response => response.json())
        .then(networks => {
            const networkSelect = document.getElementById('networks');
            networkSelect.innerHTML = ''; // Clear existing options
            networks.forEach(network => {
                const option = document.createElement('option');
                option.value = network;
                option.textContent = network;
                networkSelect.appendChild(option);
            });
            console.log('Networks loaded:', networks);
        })
        .catch(error => {
            console.error('Error fetching networks:', error);
            document.getElementById('status').textContent = 'Failed to fetch networks';
        });
}

function connectToWiFi() {
    const ssid = document.getElementById('networks').value;
    const password = document.getElementById('password').value;
    
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
        document.getElementById('status').textContent = 'Connection failed';
    });
}

// Call fetchNetworks when the page loads
document.addEventListener('DOMContentLoaded', fetchNetworks);
