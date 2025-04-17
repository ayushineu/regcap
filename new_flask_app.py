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
    # Dummy data for testing
    documents = {"doc1.pdf": ["Text chunk 1", "Text chunk 2"]}
    chat_history = [("What's a regulatory framework?", "A regulatory framework is a system of regulations and guidelines.")]
    diagrams = [("graph TD; A[Start] --> B[Process]; B --> C[End]", "A simple process diagram", "flowchart")]
    session_id = "test-session-123"
    sessions = {"test-session-123": "2025-04-15 12:00:00"}
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegCap GPT</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        :root {
            --primary-bg: #ffffff;
            --secondary-bg: #f8f9fa;
            --primary-text: #212529;
            --secondary-text: #6c757d;
            --border-color: #dee2e6;
            --primary-btn: #007bff;
            --primary-btn-hover: #0056b3;
        }
        
        [data-theme="dark"] {
            --primary-bg: #121212;
            --secondary-bg: #1e1e1e;
            --primary-text: #e0e0e0;
            --secondary-text: #aaaaaa;
            --border-color: #333333;
            --primary-btn: #0066cc;
            --primary-btn-hover: #004c99;
        }
        
        body {
            background-color: var(--primary-bg);
            color: var(--primary-text);
            transition: all 0.3s ease;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background-color: var(--secondary-bg);
            border-bottom: 1px solid var(--border-color);
        }
        
        .tab-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 160px);
            margin: 20px 0;
        }
        
        .tab-buttons {
            display: flex;
            border-bottom: 1px solid var(--border-color);
        }
        
        .tab-button {
            padding: 12px 24px;
            cursor: pointer;
            background-color: var(--secondary-bg);
            color: var(--primary-text);
            border: none;
            transition: background-color 0.3s;
        }
        
        .tab-button.active {
            background-color: var(--primary-btn);
            color: white;
        }
        
        .tab-content {
            display: none;
            padding: 20px;
            background-color: var(--primary-bg);
            border: 1px solid var(--border-color);
            border-top: none;
            flex-grow: 1;
            overflow-y: auto;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .chat-container {
            height: 300px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            padding: 10px;
            margin-bottom: 20px;
            background-color: var(--secondary-bg);
        }
        
        .user-message, .bot-message {
            padding: 10px;
            margin: 5px 0;
            border-radius: 10px;
            max-width: 80%;
        }
        
        .user-message {
            background-color: var(--primary-btn);
            color: white;
            margin-left: auto;
        }
        
        .bot-message {
            background-color: var(--secondary-bg);
            color: var(--primary-text);
            margin-right: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RegCap GPT</h1>
            <div>
                <button id="darkModeToggle" class="btn btn-outline-secondary">
                    <i class="fa fa-moon-o"></i> Dark Mode
                </button>
            </div>
        </div>
        
        <div class="tab-container">
            <div class="tab-buttons">
                <button class="tab-button active" data-tab="chat">Chat</button>
                <button class="tab-button" data-tab="documents">Documents</button>
                <button class="tab-button" data-tab="diagrams">Diagrams</button>
                <button class="tab-button" data-tab="sessions">Sessions</button>
            </div>
            
            <div id="chat" class="tab-content active">
                <h2>Chat</h2>
                <div class="chat-container">
                    {% for question, answer in chat_history %}
                    <div class="user-message">
                        <strong>You:</strong> {{ question }}
                    </div>
                    <div class="bot-message">
                        <strong>Bot:</strong> {{ answer|safe }}
                    </div>
                    {% endfor %}
                </div>
                <form id="question-form">
                    <div class="mb-3">
                        <label for="question" class="form-label">Your Question:</label>
                        <textarea class="form-control" id="question" rows="3" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Ask</button>
                </form>
            </div>
            
            <div id="documents" class="tab-content">
                <h2>Documents</h2>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <div class="mb-3">
                        <label for="document" class="form-label">Upload PDF Document:</label>
                        <input class="form-control" type="file" id="document" name="document" multiple accept=".pdf">
                    </div>
                    <button type="submit" class="btn btn-primary">Upload</button>
                </form>
                
                <div class="mt-4">
                    <h3>Uploaded Documents</h3>
                    {% if documents %}
                    <ul class="list-group">
                        {% for doc_name in documents.keys() %}
                        <li class="list-group-item">{{ doc_name }}</li>
                        {% endfor %}
                    </ul>
                    {% else %}
                    <p>No documents uploaded yet.</p>
                    {% endif %}
                </div>
            </div>
            
            <div id="diagrams" class="tab-content">
                <h2>Diagrams</h2>
                {% if diagrams %}
                {% for diagram_code, explanation, diagram_type in diagrams %}
                <div class="card mb-4">
                    <div class="card-header">
                        <h3>{{ diagram_type|capitalize }} Diagram</h3>
                    </div>
                    <div class="card-body">
                        <p><strong>Explanation:</strong> {{ explanation }}</p>
                        <div class="mermaid">
                            {{ diagram_code }}
                        </div>
                    </div>
                </div>
                {% endfor %}
                {% else %}
                <p>No diagrams generated yet. Ask a question that requires visualization.</p>
                {% endif %}
            </div>
            
            <div id="sessions" class="tab-content">
                <h2>Sessions</h2>
                <div class="mb-4">
                    <h3>Current Session</h3>
                    <p>Active Session: {{ session_id }}</p>
                    <button id="createNewSession" class="btn btn-primary">Create New Session</button>
                </div>
                
                <h3>Available Sessions</h3>
                {% if sessions %}
                <ul class="list-group">
                    {% for s_id, created_at in sessions.items() %}
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        {{ s_id }}
                        {% if s_id == session_id %}
                        <span class="badge bg-primary">Current</span>
                        {% else %}
                        <button class="btn btn-sm btn-outline-primary switch-session" data-session-id="{{ s_id }}">Switch</button>
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <p>No sessions available.</p>
                {% endif %}
            </div>
        </div>
    </div>
    
    <script>
        // Initialize mermaid
        mermaid.initialize({ startOnLoad: true });
        
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded');
            
            // Tab switching
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const tabId = this.getAttribute('data-tab');
                    console.log('Switching to tab:', tabId);
                    
                    // Hide all tab contents
                    document.querySelectorAll('.tab-content').forEach(content => {
                        content.classList.remove('active');
                    });
                    
                    // Remove active class from buttons
                    tabButtons.forEach(btn => {
                        btn.classList.remove('active');
                    });
                    
                    // Show selected tab
                    document.getElementById(tabId).classList.add('active');
                    this.classList.add('active');
                    
                    // Special handling for diagrams
                    if (tabId === 'diagrams') {
                        try {
                            mermaid.init(undefined, '.mermaid');
                        } catch(e) {
                            console.error('Error rendering diagrams:', e);
                        }
                    }
                });
            });
            
            // Dark mode toggle
            const darkModeToggle = document.getElementById('darkModeToggle');
            if (darkModeToggle) {
                console.log('Dark mode toggle found');
                
                // Check saved preference
                const savedTheme = localStorage.getItem('theme');
                const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
                
                // Apply theme based on saved preference or OS preference
                if (savedTheme === 'dark' || (!savedTheme && prefersDarkMode)) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    darkModeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                }
                
                // Toggle theme on click
                darkModeToggle.addEventListener('click', function() {
                    console.log('Dark mode toggle clicked');
                    
                    if (document.documentElement.getAttribute('data-theme') === 'dark') {
                        document.documentElement.removeAttribute('data-theme');
                        localStorage.setItem('theme', 'light');
                        darkModeToggle.innerHTML = '<i class="fa fa-moon-o"></i> Dark Mode';
                    } else {
                        document.documentElement.setAttribute('data-theme', 'dark');
                        localStorage.setItem('theme', 'dark');
                        darkModeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                    }
                    
                    // Re-render diagrams with new theme
                    setTimeout(() => {
                        try {
                            mermaid.init(undefined, '.mermaid');
                        } catch(e) {}
                    }, 100);
                });
            } else {
                console.error('Dark mode toggle not found');
            }
            
            // Form handling
            const questionForm = document.getElementById('question-form');
            if (questionForm) {
                questionForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const question = document.getElementById('question').value.trim();
                    if (question) {
                        alert('This is a demo app. In the real app, your question would be processed.');
                        document.getElementById('question').value = '';
                    }
                });
            }
            
            // Session buttons
            document.getElementById('createNewSession')?.addEventListener('click', function() {
                alert('This is a demo. In the real app, a new session would be created.');
            });
            
            document.querySelectorAll('.switch-session').forEach(button => {
                button.addEventListener('click', function() {
                    const sessionId = this.getAttribute('data-session-id');
                    alert(`This is a demo. In the real app, you would switch to session ${sessionId}.`);
                });
            });
        });
    </script>
</body>
</html>
""", documents=documents, chat_history=chat_history, diagrams=diagrams, session_id=session_id, sessions=sessions)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)