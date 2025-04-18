"""
RegCap GPT - Main entry point for deployment

This file serves as the main entry point for deploying the RegCap GPT application.
It imports and runs the Flask application from app.py.
"""

from app import app as application

# This is the standard way to deploy a Flask app
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000)