from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return """
    <html>
        <head>
            <title>Flask Test App</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                h1 {
                    color: #333;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Flask Test App</h1>
                <p>This is a simple Flask application to test if we have basic web functionality.</p>
                <p>If you're seeing this page, it means the Flask app is working!</p>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)