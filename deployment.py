"""
RegCap GPT - Deployment Service

This is a simplified deployment file that serves the RegCap application.
It automatically redirects to the main app.
"""

from flask import Flask, redirect

app = Flask(__name__)

@app.route('/')
def index():
    """Redirect to main app"""
    # This will redirect to the RegCap workflow
    return redirect("https://regulatory-intelligence-ayushisnmims.replit.app/")

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1].split('=')[1]) if len(sys.argv) > 1 and '--port=' in sys.argv[1] else 5000
    app.run(host='0.0.0.0', port=port)