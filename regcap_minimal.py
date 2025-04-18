"""
RegCap Minimal - Deployment-Ready Minimal Version

This is an extremely simplified version of RegCap for deployment, 
focusing on clean, error-free JavaScript and basic functionality.
"""

from flask import Flask, render_template_string, request, jsonify, session
import uuid
import os
import time

app = Flask(__name__)
app.secret_key = "regcap_secure_key"

@app.route('/')
def index():
    """Render the main application page."""
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegCap GPT - Minimal</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .notification {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mt-4 mb-4">RegCap GPT - Deployment Version</h1>
        
        <div class="notification">
            <strong>Deployment Notice:</strong> This is a stripped-down version of RegCap GPT designed specifically for deployment testing.
        </div>
        
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                Welcome
            </div>
            <div class="card-body">
                <h5 class="card-title">RegCap GPT is ready for deployment</h5>
                <p class="card-text">This minimal version confirms that the application can be successfully deployed.</p>
                <p>The full version includes:</p>
                <ul>
                    <li>PDF document upload and analysis</li>
                    <li>Natural language question answering</li>
                    <li>Diagram generation</li>
                    <li>Session management</li>
                </ul>
                <a href="#" class="btn btn-primary">Back to main app</a>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header bg-success text-white">
                Status
            </div>
            <div class="card-body">
                <p class="card-text">Server is running properly.</p>
                <p class="card-text">Time: <span id="current-time"></span></p>
            </div>
        </div>
    </div>
    
    <script>
        // Simple script to update the time
        function updateTime() {
            var timeElement = document.getElementById("current-time");
            if (timeElement) {
                var now = new Date();
                timeElement.textContent = now.toLocaleTimeString();
            }
        }
        
        // Update time immediately and then every second
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    import sys
    
    # Default to port 5010 to avoid conflicts
    port = 5010
    
    # Get port from command line if provided
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith('--port'):
                try:
                    port = int(arg.split('=')[1])
                except (IndexError, ValueError):
                    print("Invalid port format. Using default port 5010.")
    
    print(f"Starting RegCap Minimal on port {port}")
    app.run(host="0.0.0.0", port=port)