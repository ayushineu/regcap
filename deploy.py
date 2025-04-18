"""
RegCap GPT - Direct Deployment File

This file is designed to be used by the Replit deployment system.
It directly imports and runs the Streamlit application.
"""

import os
import sys
import subprocess

def main():
    """Run the Streamlit application for deployment."""
    # Set environment variables for Streamlit
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    os.environ['STREAMLIT_SERVER_PORT'] = '80'
    
    # Run Streamlit with the clean app
    subprocess.run([
        "streamlit", "run", "app.py", 
        "--server.port", "80",
        "--server.headless", "true",
        "--server.address", "0.0.0.0"
    ])

if __name__ == "__main__":
    main()