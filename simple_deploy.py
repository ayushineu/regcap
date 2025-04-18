"""
RegCap GPT - Super Simple Deployment Script

A streamlined deployment script for RegCap GPT that follows
Replit's requirements for deployment.
This script imports the full Flask application from app.py and serves it.
"""

import os
import logging
from datetime import datetime
import importlib.util

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('deployment')
logger.info("Simplified deployment script starting")

# Import the Flask app from app.py using importlib
try:
    logger.info("Attempting to import Flask app from app.py")
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    app = app_module.app
    logger.info("Successfully imported Flask app from app.py")
except Exception as e:
    logger.error(f"Failed to import Flask app from app.py: {e}")
    # Fallback to a simple Flask app if import fails
    from flask import Flask, jsonify, request
    app = Flask(__name__)
    logger.info("Using fallback simplified Flask app")

# Add special deployment-only endpoints that won't conflict with app.py routes
@app.route('/deployment-status')
def deployment_status():
    """Application deployment status with environment details"""
    env_vars = {
        "PORT": os.environ.get("PORT", "not set"),
        "REPL_ID": os.environ.get("REPL_ID", "not set"),
        "REPL_OWNER": os.environ.get("REPL_OWNER", "not set"),
        "REPL_SLUG": os.environ.get("REPL_SLUG", "not set"),
        "REPLIT_DEPLOYMENT": os.environ.get("REPLIT_DEPLOYMENT", "not set")
    }
    return jsonify({
        "status": "online",
        "timestamp": str(datetime.now()),
        "environment": env_vars,
        "app_type": "imported from app.py" if 'app_module' in globals() else "fallback app"
    })

@app.route('/deployment-health')
def deployment_health():
    """Deployment health check endpoint"""
    return jsonify({"status": "healthy"})

# This is necessary for Replit deployment to work correctly
if __name__ == "__main__":
    # IMPORTANT: Always use the PORT environment variable for deployment
    # This is a requirement for Replit deployments
    port = int(os.environ.get("PORT", 5000))  # Must use 5000 for Replit workflows to detect
    logger.info(f"Starting Flask application on port {port} from PORT env var: {os.environ.get('PORT', 'not set')}")
    
    # Run the app on the specified port and host
    # The host must be 0.0.0.0 to be accessible externally
    app.run(host="0.0.0.0", port=port, debug=False)