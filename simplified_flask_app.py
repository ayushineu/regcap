from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
import os
import time
import pickle
import base64
import uuid
import json
import PyPDF2
import openai
from openai import OpenAI
import numpy as np
import faiss
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    """Render the main application page."""
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>RegCap GPT</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
            background-color: #f5f5f5;
        }
        .tab-buttons {
            display: flex;
            border-bottom: 1px solid #ccc;
            margin-bottom: 20px;
        }
        .tab-button {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f1f1f1;
            margin-right: 5px;
            border: 1px solid #ccc;
            border-bottom: none;
        }
        .tab-button.active {
            background-color: #007bff;
            color: white;
            border-color: #007bff;
        }
        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #ccc;
            background-color: white;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="my-4">RegCap GPT</h1>
        
        <!-- Tab Buttons -->
        <div class="tab-buttons">
            <div class="tab-button active" data-tab="chat-tab">Chat</div>
            <div class="tab-button" data-tab="documents-tab">Documents</div>
            <div class="tab-button" data-tab="diagrams-tab">Diagrams</div>
            <div class="tab-button" data-tab="sessions-tab">Sessions</div>
        </div>
        
        <!-- Tab Contents -->
        <div id="chat-tab" class="tab-content active">
            <h2>Chat</h2>
            <div class="chat-messages mb-3 p-3 border rounded" style="height: 300px; overflow-y: auto;">
                <div class="message bot-message bg-light p-2 mb-2 rounded">
                    Welcome to RegCap GPT! Upload documents and ask questions.
                </div>
            </div>
            <form id="question-form" class="mb-3">
                <div class="mb-3">
                    <label for="question" class="form-label">Your Question:</label>
                    <textarea class="form-control" id="question" rows="3" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Ask</button>
            </form>
        </div>
        
        <div id="documents-tab" class="tab-content">
            <h2>Documents</h2>
            <form action="/upload" method="post" enctype="multipart/form-data" class="mb-3">
                <div class="mb-3">
                    <label for="document" class="form-label">Upload PDF Document:</label>
                    <input class="form-control" type="file" id="document" name="document" multiple accept=".pdf" required>
                </div>
                <button type="submit" class="btn btn-primary">Upload</button>
            </form>
            <div class="uploaded-documents mt-4">
                <h3>Uploaded Documents</h3>
                <p>No documents uploaded yet.</p>
            </div>
        </div>
        
        <div id="diagrams-tab" class="tab-content">
            <h2>Diagrams</h2>
            <p>No diagrams generated yet. Ask a question that requires visualization.</p>
        </div>
        
        <div id="sessions-tab" class="tab-content">
            <h2>Sessions</h2>
            <p>Current session management will be implemented here.</p>
        </div>
    </div>
    
    <script>
        // Simple tab switching
        document.addEventListener('DOMContentLoaded', function() {
            // Tab navigation
            const tabButtons = document.querySelectorAll('.tab-button');
            
            tabButtons.forEach(button => {
                button.addEventListener('click', function() {
                    // Get the tab to show
                    const tabId = this.getAttribute('data-tab');
                    console.log('Switching to tab:', tabId);
                    
                    // Hide all tabs and remove active class
                    document.querySelectorAll('.tab-content').forEach(tab => {
                        tab.classList.remove('active');
                    });
                    
                    document.querySelectorAll('.tab-button').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    
                    // Show the selected tab and add active class
                    document.getElementById(tabId).classList.add('active');
                    this.classList.add('active');
                });
            });
            
            // Form submission
            const questionForm = document.getElementById('question-form');
            questionForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const question = document.getElementById('question').value.trim();
                if (question) {
                    // Add user message
                    const chatMessages = document.querySelector('.chat-messages');
                    const userMessage = document.createElement('div');
                    userMessage.className = 'message user-message bg-primary text-white p-2 mb-2 rounded';
                    userMessage.textContent = question;
                    chatMessages.appendChild(userMessage);
                    
                    // Clear input
                    document.getElementById('question').value = '';
                    
                    // You would typically send this to the server here
                    // For now, just add a fake response
                    const botMessage = document.createElement('div');
                    botMessage.className = 'message bot-message bg-light p-2 mb-2 rounded';
                    botMessage.textContent = 'Please upload documents first to get answers to your queries.';
                    
                    // Add with a slight delay to simulate processing
                    setTimeout(() => {
                        chatMessages.appendChild(botMessage);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }, 500);
                }
            });
        });
    </script>
</body>
</html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
