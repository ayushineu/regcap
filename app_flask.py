"""
RegCap GPT - Flask Application Launcher

This file exists to make it clear for the Replit deployment system
that we're using Flask, not Streamlit.
"""

# Import the Flask app from our deployment file
from deployment import app

if __name__ == "__main__":
    # Set up the Flask server
    print("Starting RegCap GPT Flask application...")
    app.run(host="0.0.0.0", port=5000)