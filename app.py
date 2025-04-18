"""
RegCap GPT - Regulatory Document Analysis Platform

This application provides a web interface for uploading regulatory documents,
asking questions about their content, and receiving AI-generated answers and visualizations.
It uses vector-based search to find relevant information in documents and leverages
OpenAI's models for generating accurate responses and diagrams.

Main features:
- PDF document upload and processing
- Natural language question answering
- Mermaid diagram generation for visualizing complex regulatory processes
- Session management for organizing separate contexts
- Dark/light theme switching
- Multi-tab interface for organizing content

Author: RegCap Team
Version: 1.0.0
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import os
import time
import uuid
import threading
import json
import base64
import pickle

# Try to import optional dependencies
try:
    import openai
    import PyPDF2
    import numpy as np
    import faiss
    from werkzeug.utils import secure_filename
except ImportError as e:
    print(f"Warning: Optional dependency not available: {e}")

# Local application imports
try:
    from fix_mermaid import fix_mermaid_syntax
    from flask_app import (
        # Data storage and session management
        SimpleStorage, get_current_session, create_new_session, 
        encode_for_storage, decode_from_storage, 
        
        # Document processing
        extract_text_from_pdf, save_document_chunks, get_document_chunks, get_all_document_chunks,
        
        # Vector search and embedding
        get_embedding, create_vector_store, get_similar_chunks,
        
        # Question answering and AI content generation
        generate_answer, generate_diagram, detect_diagram_request,
        
        # History and storage management
        save_chat_history, get_chat_history, save_diagram, get_diagrams,
        list_all_sessions, log_message
    )
except ImportError:
    # For deployment where imports might fail
    def fix_mermaid_syntax(code, diagram_type):
        return code
        
    # Create dummy functions for testing deployment
    def get_current_session():
        return "session_" + str(int(time.time()))
        
    def create_new_session():
        return "session_" + str(int(time.time()))
        
    def get_document_chunks():
        return {}
        
    def get_chat_history():
        return []
        
    def get_diagrams():
        return []
        
    def list_all_sessions():
        return {"session_" + str(int(time.time())): time.time()}

# Create our question status tracking system
question_status_store = {}

def update_question_status(question_id, stage=None, progress=None, done=None, error=None):
    """Update the status of a question being processed in the background."""
    if not question_id:
        return
        
    # Initialize status object if this is a new question
    if question_id not in question_status_store:
        question_status_store[question_id] = {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "stage": "Starting",
            "progress": 0,
            "done": False,
            "error": None
        }
    
    # Update status values as requested
    current_status = question_status_store[question_id]
    
    if stage:
        current_status["stage"] = stage
        print(f"Question {question_id}: {stage}")
        
    if progress is not None:
        current_status["progress"] = progress
        
    if done is not None:
        current_status["done"] = done
        if done:
            print(f"Question {question_id}: Processing complete")
            
    if error:
        current_status["error"] = error
        print(f"Question {question_id} ERROR: {error}")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize OpenAI client with error handling
try:
    openai.api_key = os.environ.get("OPENAI_API_KEY")
except:
    pass  # Will be handled in routes

@app.route('/')
def index():
    """Render the main application page."""
    try:
        # Get data from the storage
        session_id = get_current_session()
        documents = get_document_chunks()
        chat_history = get_chat_history()
        raw_diagrams = get_diagrams()
        sessions = list_all_sessions()
        
        # Process diagrams to fix any Mermaid syntax issues
        # Only process unique diagrams to avoid duplicates
        seen_diagrams = set()
        diagrams = []
        
        for diagram_code, explanation, diagram_type in raw_diagrams:
            # Create a unique identifier for this diagram
            diagram_id = f"{explanation}-{diagram_type}"
            
            # Skip if we've already seen this diagram
            if diagram_id in seen_diagrams:
                continue
                
            # Mark this diagram as seen
            seen_diagrams.add(diagram_id)
            
            # Fix Mermaid syntax and add to the list
            fixed_code = fix_mermaid_syntax(diagram_code, diagram_type)
            diagrams.append((fixed_code, explanation, diagram_type))
    except Exception as e:
        # For deployment testing, provide fallbacks
        session_id = "test_session"
        documents = {}
        chat_history = []
        diagrams = []
        sessions = {"test_session": time.time()}
        print(f"Error in index: {str(e)}")
    
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
        /* Core styles */
        :root {
            --primary-color: #4f46e5;
            --primary-hover: #4338ca;
            --secondary-color: #64748b;
            --accent-color: #f97316;
            --primary-bg: #ffffff;
            --secondary-bg: #f8fafc;
            --tertiary-bg: #f1f5f9;
            --primary-text: #0f172a;
            --secondary-text: #475569;
            --light-text: #ffffff;
            --border-color: #e2e8f0;
            --border-radius: 8px;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.08);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.05);
        }
        
        [data-theme="dark"] {
            --primary-color: #6366f1;
            --primary-hover: #818cf8;
            --secondary-color: #94a3b8;
            --accent-color: #fb923c;
            --primary-bg: #111827;
            --secondary-bg: #1e293b;
            --tertiary-bg: #334155;
            --primary-text: #f1f5f9;
            --secondary-text: #cbd5e1;
            --light-text: #ffffff;
            --border-color: #475569;
        }
        
        body {
            background-color: var(--primary-bg);
            color: var(--primary-text);
            transition: all 0.3s ease;
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.5;
            margin: 0;
            padding: 0;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Beta banner */
        .beta-banner {
            background-color: #eef2ff;
            border: 1px solid #e0e7ff;
            border-radius: 4px;
            padding: 0.3rem 1rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        [data-theme="dark"] .beta-banner {
            background-color: #312e81;
            border-color: #4338ca;
        }
        
        .beta-banner-content {
            color: #4338ca;
            font-size: 0.8rem;
        }
        
        [data-theme="dark"] .beta-banner-content {
            color: #c7d2fe;
        }
        
        .beta-close-btn {
            background: none;
            border: none;
            color: #4338ca;
            cursor: pointer;
            font-size: 1.2rem;
            padding: 0;
            margin-left: 0.5rem;
        }
        
        .beta-close-btn:hover {
            color: #3730a3;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem 2rem;
            background: linear-gradient(to right, var(--primary-color), var(--primary-hover));
            border-radius: var(--border-radius);
            margin-bottom: 2rem;
            box-shadow: var(--shadow-md);
        }
        
        .header h1 {
            color: var(--light-text);
            margin: 0;
            font-weight: 700;
        }
        
        .theme-toggle {
            background-color: rgba(255, 255, 255, 0.2);
            color: var(--light-text);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .theme-toggle:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }
        
        /* Tab system */
        .tab-container {
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            background-color: var(--secondary-bg);
        }
        
        .tab-buttons {
            display: flex;
            background-color: var(--tertiary-bg);
            padding: 0.75rem;
            gap: 0.5rem;
        }
        
        .tab-button {
            padding: 0.75rem 1.5rem;
            cursor: pointer;
            background-color: var(--secondary-bg);
            color: var(--secondary-text);
            border: none;
            border-radius: var(--border-radius);
            transition: all 0.2s ease;
            font-weight: 500;
            box-shadow: var(--shadow-sm);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .tab-button:hover {
            background-color: var(--tertiary-bg);
        }
        
        .tab-button.active {
            background-color: var(--primary-color);
            color: var(--light-text);
            box-shadow: var(--shadow-md);
        }
        
        .tab-content {
            display: none;
            padding: 2rem;
            background-color: var(--primary-bg);
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Content styles */
        .chat-container {
            height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            background-color: var(--secondary-bg);
            border-radius: var(--border-radius);
        }
        
        .user-message, .bot-message {
            padding: 1rem 1.25rem;
            margin: 0.75rem 0;
            border-radius: 1rem;
            max-width: 85%;
            box-shadow: var(--shadow-sm);
        }
        
        .user-message {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
            color: var(--light-text);
            margin-left: auto;
            border-bottom-right-radius: 0.25rem;
        }
        
        .bot-message {
            background-color: var(--tertiary-bg);
            color: var(--primary-text);
            margin-right: auto;
            border-bottom-left-radius: 0.25rem;
        }
        
        /* Form elements */
        .form-control, .btn {
            border-radius: var(--border-radius);
            font-size: 1rem;
            padding: 0.75rem 1rem;
        }
        
        .btn-primary {
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }
        
        .btn-primary:hover {
            background-color: var(--primary-hover);
            border-color: var(--primary-hover);
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
            
            .tab-buttons {
                flex-wrap: wrap;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Beta Banner -->
        <div id="betaBanner" class="beta-banner">
            <div class="beta-banner-content">
                <i class="fa fa-wrench"></i> This application is in beta. Your feedback will help us improve.
            </div>
            <button class="beta-close-btn" onclick="document.getElementById('betaBanner').style.display='none';">&times;</button>
        </div>
        
        <!-- Header -->
        <div class="header">
            <h1><i class="fa fa-book"></i> RegCap GPT</h1>
            <button id="themeToggle" class="theme-toggle">
                <i class="fa fa-moon-o"></i> Dark Mode
            </button>
        </div>
        
        <!-- Main Tab Navigation -->
        <div class="tab-container">
            <div class="tab-buttons">
                <button class="tab-button active" data-tab="chat-tab">
                    <i class="fa fa-comments"></i> Chat
                </button>
                <button class="tab-button" data-tab="docs-tab">
                    <i class="fa fa-file-pdf-o"></i> Documents
                </button>
                <button class="tab-button" data-tab="diagrams-tab">
                    <i class="fa fa-sitemap"></i> Diagrams
                </button>
                <button class="tab-button" data-tab="sessions-tab">
                    <i class="fa fa-database"></i> Sessions
                </button>
            </div>
            
            <!-- Chat Tab -->
            <div id="chat-tab" class="tab-content active">
                <h2><i class="fa fa-comments"></i> Chat with your Documents</h2>
                
                <div class="chat-container" id="chatMessages">
                    {% if chat_history %}
                        {% for question, answer in chat_history %}
                            <div class="user-message">
                                <strong>You:</strong> {{ question }}
                            </div>
                            <div class="bot-message">
                                <strong>RegCap GPT:</strong> {{ answer }}
                            </div>
                        {% endfor %}
                    {% else %}
                        <div class="text-center text-muted my-5">
                            <i class="fa fa-info-circle fa-2x mb-3"></i>
                            <p>No chat history yet. Upload documents and start asking questions!</p>
                        </div>
                    {% endif %}
                </div>
                
                <form id="questionForm" class="mb-4">
                    <div class="input-group mb-3">
                        <input type="text" id="questionInput" class="form-control" 
                            placeholder="Ask a question about your documents..." required>
                        <button class="btn btn-primary" type="submit">
                            <i class="fa fa-paper-plane"></i> Send
                        </button>
                    </div>
                </form>
                
                <div class="alert alert-info" role="alert">
                    <i class="fa fa-lightbulb-o"></i> <strong>Tip:</strong> 
                    You can ask for diagrams by using phrases like "create a flowchart", 
                    "draw a diagram", or "visualize the process".
                </div>
            </div>
            
            <!-- Documents Tab -->
            <div id="docs-tab" class="tab-content">
                <h2><i class="fa fa-file-pdf-o"></i> Document Management</h2>
                
                <div class="card mb-4">
                    <div class="card-header" style="background-color: var(--primary-color); color: var(--light-text);">
                        <h5 class="card-title mb-0">Upload Documents</h5>
                    </div>
                    <div class="card-body">
                        <form id="uploadForm" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label for="documentUpload" class="form-label">
                                    Select PDF files to upload:
                                </label>
                                <input class="form-control" type="file" id="documentUpload" 
                                    name="files" multiple accept=".pdf">
                            </div>
                            <button type="submit" class="btn btn-primary">
                                <i class="fa fa-upload"></i> Upload & Process
                            </button>
                        </form>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header" style="background-color: var(--primary-color); color: var(--light-text);">
                        <h5 class="card-title mb-0">Uploaded Documents</h5>
                    </div>
                    <div class="card-body">
                        {% if documents %}
                            <div class="list-group">
                                {% for doc_name in documents.keys() %}
                                    <div class="list-group-item">
                                        <i class="fa fa-file-pdf-o"></i> {{ doc_name }}
                                        <span class="badge bg-secondary float-end">
                                            {{ documents[doc_name]|length }} chunks
                                        </span>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <div class="text-center text-muted my-4">
                                <i class="fa fa-folder-open-o fa-2x mb-3"></i>
                                <p>No documents have been uploaded yet.</p>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <!-- Diagrams Tab -->
            <div id="diagrams-tab" class="tab-content">
                <h2><i class="fa fa-sitemap"></i> Generated Diagrams</h2>
                
                {% if diagrams %}
                    {% for diagram_code, explanation, diagram_type in diagrams %}
                        <div class="card mb-4">
                            <div class="card-header" style="background-color: var(--primary-color); color: var(--light-text);">
                                <h5 class="card-title mb-0">
                                    {{ diagram_type|capitalize }} Diagram
                                </h5>
                            </div>
                            <div class="card-body">
                                <div class="mb-3">
                                    <h6 class="text-primary">Explanation:</h6>
                                    <p>{{ explanation }}</p>
                                </div>
                                <div class="diagram-container">
                                    <div class="mermaid">
                                        {{ diagram_code }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="text-center text-muted my-5">
                        <i class="fa fa-sitemap fa-2x mb-3"></i>
                        <p>No diagrams have been generated yet. Ask a question that requires visualization!</p>
                    </div>
                {% endif %}
            </div>
            
            <!-- Sessions Tab -->
            <div id="sessions-tab" class="tab-content">
                <h2><i class="fa fa-database"></i> Session Management</h2>
                
                <div class="alert alert-info">
                    <i class="fa fa-info-circle"></i> 
                    <strong>Current Session:</strong> {{ session_id }}
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header" style="background-color: var(--primary-color); color: var(--light-text);">
                                <h5 class="card-title mb-0">Create New Session</h5>
                            </div>
                            <div class="card-body">
                                <p>Create a new session to start with a clean slate:</p>
                                <button id="newSessionBtn" class="btn btn-primary">
                                    <i class="fa fa-plus-circle"></i> New Session
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header" style="background-color: var(--primary-color); color: var(--light-text);">
                                <h5 class="card-title mb-0">Available Sessions</h5>
                            </div>
                            <div class="card-body">
                                {% if sessions %}
                                    <div class="list-group">
                                        {% for session_id, timestamp in sessions.items() %}
                                            <button class="list-group-item list-group-item-action session-switch-btn"
                                                data-session-id="{{ session_id }}">
                                                <i class="fa fa-clock-o"></i> 
                                                {{ session_id }}
                                            </button>
                                        {% endfor %}
                                    </div>
                                {% else %}
                                    <div class="text-center text-muted">
                                        <p>No previous sessions found.</p>
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <footer class="mt-5 pt-3 border-top text-center text-muted">
            <p><i class="fa fa-code"></i> RegCap GPT - Regulatory Document Analysis Platform</p>
            <p class="small">Version 1.0.0 - Made with <i class="fa fa-heart text-danger"></i> by RegCap Team</p>
        </footer>
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
            
            // Theme toggle
            var themeToggle = document.getElementById('themeToggle');
            var savedTheme = localStorage.getItem('theme');
            
            // Apply saved theme
            if (savedTheme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                themeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
            }
            
            // Toggle theme on click
            themeToggle.addEventListener('click', function() {
                if (document.documentElement.getAttribute('data-theme') === 'dark') {
                    document.documentElement.removeAttribute('data-theme');
                    localStorage.setItem('theme', 'light');
                    themeToggle.innerHTML = '<i class="fa fa-moon-o"></i> Dark Mode';
                } else {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                    themeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                }
            });
            
            // Initialize Mermaid diagrams
            if (typeof mermaid !== 'undefined') {
                mermaid.initialize({
                    startOnLoad: true,
                    securityLevel: 'loose',
                    theme: 'default',
                    flowchart: {
                        htmlLabels: true,
                        useMaxWidth: true,
                        curve: 'linear'
                    }
                });
            }
            
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
                        var userDiv = document.createElement('div');
                        userDiv.className = 'user-message';
                        userDiv.innerHTML = '<strong>You:</strong> ' + question;
                        chatMessages.appendChild(userDiv);
                        
                        // Clear input
                        questionInput.value = '';
                        
                        // Scroll to bottom
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        // Add temporary processing message
                        var processingDiv = document.createElement('div');
                        processingDiv.className = 'bot-message';
                        processingDiv.innerHTML = '<strong>RegCap GPT:</strong> Processing...';
                        chatMessages.appendChild(processingDiv);
                        
                        // Simulate response (would be replaced with actual API call)
                        setTimeout(function() {
                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> This is a placeholder response. In the real application, this would be generated by analyzing your documents using AI.';
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }, 1500);
                    }
                });
            }
            
            // File upload handling
            var uploadForm = document.getElementById('uploadForm');
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    var fileInput = document.getElementById('documentUpload');
                    if (fileInput.files.length > 0) {
                        alert('File upload simulation: In the real application, this would process your documents.');
                        fileInput.value = '';
                    } else {
                        alert('Please select at least one file to upload.');
                    }
                });
            }
            
            // New session button
            var newSessionBtn = document.getElementById('newSessionBtn');
            if (newSessionBtn) {
                newSessionBtn.addEventListener('click', function() {
                    if (confirm('Create a new session? This will start with a clean slate.')) {
                        alert('New session simulation: In the real application, this would create a new session.');
                    }
                });
            }
            
            // Session switch buttons
            var sessionSwitchBtns = document.querySelectorAll('.session-switch-btn');
            for (var s = 0; s < sessionSwitchBtns.length; s++) {
                sessionSwitchBtns[s].addEventListener('click', function() {
                    var sessionId = this.getAttribute('data-session-id');
                    if (confirm('Switch to session ' + sessionId + '?')) {
                        alert('Session switch simulation: In the real application, this would switch to the selected session.');
                    }
                });
            }
        });
    </script>
</body>
</html>
    """, 
        session_id=session_id,
        documents=documents,
        chat_history=chat_history,
        diagrams=diagrams,
        sessions=sessions
    )

@app.route('/new-session', methods=['POST'])
def new_session():
    """Create a new session."""
    try:
        session_id = create_new_session()
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/switch-session', methods=['POST'])
def switch_session():
    """Switch to a different session."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        # This would be implemented with actual session switching logic
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload-files', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    try:
        # This would be implemented with actual file processing logic
        return jsonify({'success': True, 'message': 'Files processed successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ask-question', methods=['POST'])
def ask_question():
    """Handle questions from the user."""
    try:
        data = request.get_json()
        question = data.get('question')
        question_id = f"q_{time.time()}"
        # This would be implemented with actual question processing logic
        return jsonify({'success': True, 'question_id': question_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/question-status/<question_id>', methods=['GET'])
def get_question_status(question_id):
    """Get the status of a specific question."""
    if question_id in question_status_store:
        return jsonify(question_status_store[question_id])
    return jsonify({'error': 'Question ID not found'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)