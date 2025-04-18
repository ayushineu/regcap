"""
RegCap GPT - Deployment Script (Flask)

This is a dedicated deployment script for the RegCap Flask application,
configured specifically for Replit's deployment system.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Initializing RegCap Flask Deployment Script")

try:
    from app import app  # Import the Flask app
    logger.info("Successfully imported Flask app from app.py")
except Exception as e:
    logger.error(f"Error importing Flask app: {str(e)}")
    raise

# For handling WSGI deployments - required by Replit
application = app

if __name__ == "__main__":
    # Print information about the environment
    logger.info("Starting RegCap Flask Application...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Running in directory: {os.getcwd()}")
    logger.info(f"Environment variables: PORT={os.environ.get('PORT')}")
    
    # Make sure we're not in Streamlit mode
    if any(arg.startswith("--server") for arg in sys.argv):
        logger.warning("Streamlit flags detected, but this is a Flask app!")
        # Remove Streamlit arguments to prevent conflicts
        sys.argv = [arg for arg in sys.argv if not arg.startswith("--server")]
    
    # Run the Flask application
    try:
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"Starting Flask app on port {port}")
        app.run(host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"Error starting Flask app: {str(e)}")
        raise