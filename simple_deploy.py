"""
RegCap GPT - Super Simple Deployment Script

A streamlined deployment script for RegCap GPT that follows
Replit's requirements for deployment.
"""

from flask import Flask, jsonify
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deployment')
logger.info("Simplified deployment script starting")

# Create a basic Flask application
app = Flask(__name__)

@app.route('/')
def index():
    """Simple home page to verify deployment is working"""
    return jsonify({
        "status": "success",
        "message": "RegCap GPT API is online",
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

# This is necessary for Replit deployment to work correctly
if __name__ == "__main__":
    # Get port from environment or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask application on port {port}")
    
    # Run the app on the specified port and host
    app.run(host="0.0.0.0", port=port, debug=False)