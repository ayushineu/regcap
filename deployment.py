"""
RegCap GPT - Deployment Service

This is a simplified deployment file that serves the RegCap application.
It automatically redirects to the main app.
"""

from flask import Flask, render_template, redirect
import sys
import os

app = Flask(__name__)

@app.route('/')
def index():
    """Render the main application page."""
    # For deployment, we'll use the original app.py functionality
    from app import app as regcap_app
    
    # Create a test client to get the rendered template
    with regcap_app.test_client() as client:
        response = client.get('/')
        return response.data
        
    # Fallback if the above doesn't work
    return "Please visit the RegCap application at the correct URL."

if __name__ == '__main__':
    port = 8080  # Default deployment port
    
    # Check for port in command line args
    if len(sys.argv) > 1 and sys.argv[1].startswith('--port='):
        port = int(sys.argv[1].split('=')[1])
    
    app.run(host='0.0.0.0', port=port)