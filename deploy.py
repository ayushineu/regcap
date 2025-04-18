"""
RegCap GPT - Direct Deployment File

This file is designed to be used by the Replit deployment system.
It directly imports and runs the Flask application.
"""

# Import the Flask app from app.py
from app import app

# This is needed for proper Replit deployment
if __name__ == "__main__":
    # The deployment system will provide the port via environment variable
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)