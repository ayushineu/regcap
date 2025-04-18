"""
Minimal Flask application to test tab functionality
"""

from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tab Test</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .container {
            max-width: 800px;
            margin: 2rem auto;
        }
        .tab-button {
            padding: 10px 20px;
            margin-right: 5px;
            background-color: #f0f0f0;
            border: none;
            cursor: pointer;
        }
        .tab-button.active {
            background-color: #2563eb;
            color: white;
        }
        .tab-content {
            display: none;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin-top: 10px;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tab Testing App</h1>
        
        <div class="tab-buttons">
            <button class="tab-button active" data-tab="tab1">Tab 1</button>
            <button class="tab-button" data-tab="tab2">Tab 2</button>
            <button class="tab-button" data-tab="tab3">Tab 3</button>
        </div>
        
        <div id="tab1" class="tab-content active">
            <h2>Tab 1 Content</h2>
            <p>This is the content for tab 1.</p>
        </div>
        
        <div id="tab2" class="tab-content">
            <h2>Tab 2 Content</h2>
            <p>This is the content for tab 2.</p>
        </div>
        
        <div id="tab3" class="tab-content">
            <h2>Tab 3 Content</h2>
            <p>This is the content for tab 3.</p>
        </div>
    </div>
    
    <script>
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            // Get all tab buttons
            var tabButtons = document.querySelectorAll('.tab-button');
            
            // Add click event to each button
            for (var i = 0; i < tabButtons.length; i++) {
                tabButtons[i].addEventListener('click', function() {
                    // Get the tab id from data-tab attribute
                    var tabId = this.getAttribute('data-tab');
                    
                    // Hide all tab contents
                    var tabContents = document.querySelectorAll('.tab-content');
                    for (var j = 0; j < tabContents.length; j++) {
                        tabContents[j].classList.remove('active');
                    }
                    
                    // Remove active class from all buttons
                    for (var k = 0; k < tabButtons.length; k++) {
                        tabButtons[k].classList.remove('active');
                    }
                    
                    // Show the selected tab content
                    document.getElementById(tabId).classList.add('active');
                    
                    // Add active class to clicked button
                    this.classList.add('active');
                });
            }
        });
    </script>
</body>
</html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)