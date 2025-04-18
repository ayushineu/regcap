"""
RegCap GPT - New Flask Implementation

A streamlined version of the RegCap GPT application with simplified
JavaScript integration and improved error handling.
"""

from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
import os
import time
import json
import threading

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Simple in-memory storage
documents = {}
chat_history = []
diagrams = []

@app.route('/')
def index():
    """Render the main application page."""
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegCap GPT</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
            font-family: 'Arial', sans-serif;
        }
        .container {
            max-width: 1000px;
            margin: 2rem auto;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .header {
            background-color: #2563eb;
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }
        .chat-container {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 8px;
        }
        .user-message, .bot-message {
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            max-width: 80%;
        }
        .user-message {
            background-color: #e9ecef;
            margin-left: auto;
        }
        .bot-message {
            background-color: #e3f2fd;
            margin-right: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="text-center">RegCap GPT</h1>
            <p class="text-center mb-0">Regulatory Document Analysis Platform</p>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-12">
                <h3>Upload Documents</h3>
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="mb-3">
                        <input class="form-control" type="file" id="documentUpload" 
                            name="files" multiple accept=".pdf">
                    </div>
                    <button type="submit" class="btn btn-primary">Upload & Process</button>
                </form>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-12">
                <h3>Chat</h3>
                <div class="chat-container" id="chatMessages">
                    <!-- Messages will appear here -->
                    <div class="text-center text-muted my-5">
                        <p>Upload documents and start asking questions!</p>
                    </div>
                </div>
                <form id="questionForm">
                    <div class="input-group mb-3">
                        <input type="text" id="questionInput" class="form-control" 
                            placeholder="Ask a question..." required>
                        <button class="btn btn-primary" type="submit">Send</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Handle question form submission
            const questionForm = document.getElementById('questionForm');
            const chatMessages = document.getElementById('chatMessages');
            
            if (questionForm) {
                questionForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const questionInput = document.getElementById('questionInput');
                    const question = questionInput.value.trim();
                    
                    if (question) {
                        // Add user message to chat
                        const userDiv = document.createElement('div');
                        userDiv.className = 'user-message';
                        userDiv.innerHTML = '<strong>You:</strong> ' + question;
                        chatMessages.appendChild(userDiv);
                        
                        // Clear input
                        questionInput.value = '';
                        
                        // Scroll to bottom
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        // Add temporary processing message
                        const processingDiv = document.createElement('div');
                        processingDiv.className = 'bot-message';
                        processingDiv.innerHTML = '<strong>RegCap GPT:</strong> Processing...';
                        chatMessages.appendChild(processingDiv);
                        
                        // Simulate response (would be replaced with actual API call)
                        setTimeout(function() {
                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> This is a placeholder response. The actual AI response would appear here.';
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }, 1500);
                    }
                });
            }
            
            // Handle file upload form
            const uploadForm = document.getElementById('uploadForm');
            
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const fileInput = document.getElementById('documentUpload');
                    if (fileInput.files.length > 0) {
                        // Show success message (would be replaced with actual API call)
                        alert('Upload successful! (This is a placeholder response)');
                        fileInput.value = '';
                    } else {
                        alert('Please select at least one file to upload.');
                    }
                });
            }
        });
    </script>
</body>
</html>
    """)

@app.route('/upload-files', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    try:
        # Process files
        return jsonify({
            'success': True,
            'message': 'Files processed successfully!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run the RegCap GPT Flask application')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the application on')
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port)