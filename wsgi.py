"""
RegCap WSGI Entry Point

This file serves as the WSGI entry point for the RegCap application,
which is the standard way many Python web servers interface with applications.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('wsgi')
logger.info("WSGI entry point loaded")

try:
    # Import the Flask app directly
    from app import app as application
    logger.info("Successfully imported Flask app for WSGI")
except Exception as e:
    logger.error(f"Failed to import Flask app: {str(e)}")
    # Re-raise to ensure error is visible
    raise

# This is the WSGI callable that deployment systems will look for
# Do not rename this variable
logger.info("WSGI application ready")

# When run directly, start the server
if __name__ == "__main__":
    logger.info("Starting Flask server via WSGI entry point")
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Using port: {port}")
    
    # Run the application
    application.run(host="0.0.0.0", port=port)