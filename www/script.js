// script.js

// Log a message to the console to confirm that the script is loaded
console.log("JavaScript is working!");

// Change the text content of the paragraph when the page loads
document.addEventListener("DOMContentLoaded", function() {
    const paragraph = document.querySelector("p");
    if (paragraph) {
        paragraph.textContent = "Welcome! You are now connected to the ESP32 Captive Portal with custom styles and scripts.";
    }
});