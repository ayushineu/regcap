"""
RegCap GPT - Deployment File for Replit

This file is used to start the Streamlit app for deployment.
"""

import os
import sys
import subprocess

def main():
    """Run the Streamlit application for deployment."""
    # Set environment variables for Streamlit
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    
    # Get port from environment or use default
    port = os.environ.get('PORT', '5000')
    print(f"Starting Streamlit app on port {port}")
    
    # Run Streamlit with the clean app
    subprocess.run([
        "streamlit", "run", "clean_app.py", 
        "--server.port", port,
        "--server.headless", "true",
        "--server.address", "0.0.0.0"
    ])

if __name__ == "__main__":
    main()