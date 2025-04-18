"""
RegCap GPT - Flask Application (Not Streamlit)

This application is a Flask app, NOT a Streamlit app. 
This file exists to clarify for the Replit deployment system 
that we're not using Streamlit.

The actual application is in app.py.
"""

# Import the Flask app
from deployment import app

# This is for Replit's deployment system
if __name__ == "__main__":
    # Print clarification message
    print("This is a Flask application, not a Streamlit application.")
    print("Starting Flask server...")
    
    # Run the app
    app.run(host="0.0.0.0", port=5000)