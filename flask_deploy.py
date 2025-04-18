"""
RegCap GPT - Deployment Script (Flask)

This is a dedicated deployment script for the RegCap Flask application,
configured specifically for Replit's deployment system.
"""

import os
import sys
from app import app  # Import the Flask app

# For handling WSGI deployments - required by Replit
application = app

if __name__ == "__main__":
    # Print information about the environment
    print("Starting RegCap Flask Application...")
    print(f"Python version: {sys.version}")
    print(f"Running in directory: {os.getcwd()}")
    
    # Make sure we're not in Streamlit mode
    if "--server.headless" in sys.argv:
        print("WARNING: Streamlit flags detected, but this is a Flask app!")
        # Remove Streamlit arguments to prevent conflicts
        sys.argv = [arg for arg in sys.argv if not arg.startswith("--server")]
    
    # Run the Flask application
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)