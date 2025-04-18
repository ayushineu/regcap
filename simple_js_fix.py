"""
Simple JavaScript Fix - RegCap GPT

A very simplified version focusing on fixing JavaScript errors
"""

from flask import Flask, render_template_string, request, jsonify, session
import uuid
import os
import time

app = Flask(__name__)
app.secret_key = "regcap_secure_key"

@app.route('/')
def index():
    """Render the main application page."""
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegCap GPT - Simplified</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .chat-container {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #f8f9fa;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
        }
        .bot-message {
            background-color: #e9ecef;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mt-4 mb-4">RegCap GPT - Simplified</h1>
        
        <div class="chat-container" id="chatMessages">
            <div class="text-center text-muted my-5">
                <p>Chat history will appear here.</p>
            </div>
        </div>
        
        <form id="questionForm" class="mb-4">
            <div class="input-group mb-3">
                <input type="text" id="questionInput" class="form-control" 
                    placeholder="Ask a question..." required>
                <button class="btn btn-primary" type="submit">Send</button>
            </div>
        </form>
        
        <div class="alert alert-info">
            <strong>Status:</strong> <span id="statusMessage">Ready</span>
        </div>
    </div>
    
    <script>
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            console.log("DOM loaded");
            
            // Form handling for question submission
            var questionForm = document.getElementById('questionForm');
            if (questionForm) {
                questionForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    var questionInput = document.getElementById('questionInput');
                    var question = questionInput.value.trim();
                    
                    if (question) {
                        // Add user message to chat
                        var chatMessages = document.getElementById('chatMessages');
                        var statusMessage = document.getElementById('statusMessage');
                        
                        // Clear "No chat history" message if it exists
                        if (chatMessages.querySelector('.text-center.text-muted')) {
                            chatMessages.innerHTML = ''; // Clear the message
                        }
                        
                        var userDiv = document.createElement('div');
                        userDiv.className = 'user-message';
                        userDiv.innerHTML = '<strong>You:</strong> ' + question;
                        chatMessages.appendChild(userDiv);
                        
                        // Add bot response (for testing)
                        var botDiv = document.createElement('div');
                        botDiv.className = 'bot-message';
                        botDiv.innerHTML = '<strong>RegCap GPT:</strong> This is a simplified test response.';
                        chatMessages.appendChild(botDiv);
                        
                        // Clear input
                        questionInput.value = '';
                        
                        // Update status
                        statusMessage.textContent = 'Message sent and response received.';
                        
                        // Scroll to bottom
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                });
            }
        });
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    import sys
    port = 5005
    
    # Get port from command line if provided
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith('--port'):
                try:
                    port = int(arg.split('=')[1])
                except (IndexError, ValueError):
                    print("Invalid port format. Using default port 5005.")
    
    print(f"Starting simplified app on port {port}")
    app.run(host="0.0.0.0", port=port)