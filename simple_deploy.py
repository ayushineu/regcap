"""
RegCap GPT - Super Simple Deployment Script

A streamlined deployment script for RegCap GPT that follows
Replit's requirements for deployment.
"""

from flask import Flask, jsonify, request
import os
import logging
from datetime import datetime

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
    
@app.route('/status')
def status():
    """Application status with environment details"""
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
        "environment": env_vars
    })

@app.route('/upload-files', methods=['POST'])
def upload_files():
    """File upload endpoint placeholder for deployment tests"""
    return jsonify({
        "status": "success", 
        "message": "File upload endpoint registered for deployment",
        "note": "This is a simplified endpoint for deployment testing only"
    })
    
@app.route('/ask-question', methods=['POST'])
def ask_question():
    """Question handling endpoint placeholder for deployment tests"""
    return jsonify({
        "status": "success", 
        "message": "Question handling endpoint registered for deployment",
        "note": "This is a simplified endpoint for deployment testing only"
    })

# This is necessary for Replit deployment to work correctly
if __name__ == "__main__":
    # IMPORTANT: Always use the PORT environment variable for deployment
    # This is a requirement for Replit deployments
    port = int(os.environ.get("PORT", 5000))  # Must use 5000 for Replit workflows to detect
    logger.info(f"Starting Flask application on port {port} from PORT env var: {os.environ.get('PORT', 'not set')}")
    
    # Run the app on the specified port and host
    # The host must be 0.0.0.0 to be accessible externally
    app.run(host="0.0.0.0", port=port, debug=False)