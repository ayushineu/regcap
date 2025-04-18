"""
RegCap GPT - Production Deployment File

This file is the single entry point for deploying the RegCap application.
It runs the Streamlit app.py file with the correct configuration.
"""

import os
import sys
import subprocess

def main():
    """Run the Streamlit application in production mode."""
    print("Starting RegCap GPT deployment...")
    
    # Set environment variables for Streamlit
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    os.environ['STREAMLIT_SERVER_PORT'] = '5000'
    
    try:
        # Run Streamlit with app.py on port 5000
        result = subprocess.run([
            "streamlit", "run", "app.py", 
            "--server.port", "5000",
            "--server.headless", "true",
            "--server.address", "0.0.0.0"
        ], check=True)
        return result.returncode
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())