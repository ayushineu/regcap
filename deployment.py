"""
RegCap GPT - Deployment Entry Point

This file serves as the dedicated entry point for deploying the RegCap application.
It imports the Flask app from app.py and runs it with the correct host and port configuration.
"""

from app import app as flask_app

# This is the entry point for deployment
# The app name must be 'app' for Replit deployment
app = flask_app

if __name__ == "__main__":
    # For manual running
    app.run(host="0.0.0.0", port=5000)