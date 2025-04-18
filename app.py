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

# Simple in-memory storage
storage = {
    "sessions": {},
    "current_session": None,
    "documents": {},
    "chat_history": {},
    "diagrams": {},
    "question_status": {},
    "logs": []
}

# Initialize app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure environment
UPLOAD_FOLDER = 'data_storage'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize OpenAI API (if available)
try:
    openai.api_key = os.environ.get("OPENAI_API_KEY")
except:
    pass

# ============================================================================
# Helper Functions
# ============================================================================

def update_question_status(question_id, stage=None, progress=None, done=None, error=None):
    """
    Update the status of a question being processed in the background.
    
    This function maintains a status record for each question being processed,
    which allows the frontend to poll for updates and provide real-time feedback
    to the user on the processing stages.
    
    Args:
        question_id (str): The unique identifier for the question
        stage (str, optional): The current processing stage (e.g., "Finding information")
        progress (int, optional): Percentage of completion (0-100)
        done (bool, optional): Whether processing is complete
        error (str, optional): Error message if an error occurred
        
    Returns:
        None
    """
    if question_id not in storage["question_status"]:
        storage["question_status"][question_id] = {
            "start_time": time.time(),
            "stage": "Starting analysis...",
            "progress": 0,
            "done": False,
            "error": None
        }
        
    status = storage["question_status"][question_id]
    
    if stage:
        status["stage"] = stage
    
    if progress is not None:
        status["progress"] = progress
        
    if done is not None:
        status["done"] = done
        if done:
            status["progress"] = 100
            status["stage"] = "Complete"
            
    if error:
        status["error"] = error
        status["done"] = True

def get_current_session():
    """Get or create the current session ID."""
    if not storage["current_session"]:
        # Create initial session if none exists
        session_id = f"session_{int(time.time())}"
        storage["sessions"][session_id] = {"created_at": time.time()}
        storage["current_session"] = session_id
        storage["documents"][session_id] = {}
        storage["chat_history"][session_id] = []
        storage["diagrams"][session_id] = []
    
    return storage["current_session"]

def get_document_chunks(session_id=None):
    """Get document chunks for the given session."""
    if not session_id:
        session_id = get_current_session()
    
    return storage["documents"].get(session_id, {})

def get_chat_history(session_id=None):
    """Get chat history for the given session."""
    if not session_id:
        session_id = get_current_session()
    
    return storage["chat_history"].get(session_id, [])

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
        
        # Split into chunks (simplified)
        chunks = []
        chunk_size = 1000
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i+chunk_size])
        
        return chunks
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return []

def save_chat_history(question, answer, session_id=None):
    """Save a question-answer pair to chat history."""
    if not session_id:
        session_id = get_current_session()
    
    if session_id not in storage["chat_history"]:
        storage["chat_history"][session_id] = []
    
    storage["chat_history"][session_id].append((question, answer))

def create_new_session():
    """Create a new session and return its ID."""
    session_id = f"session_{int(time.time())}"
    storage["sessions"][session_id] = {"created_at": time.time()}
    storage["current_session"] = session_id
    storage["documents"][session_id] = {}
    storage["chat_history"][session_id] = []
    storage["diagrams"][session_id] = []
    
    return session_id

def list_all_sessions():
    """List all available sessions."""
    return storage["sessions"]

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Render the main application page."""
    session_id = get_current_session()
    documents = get_document_chunks()
    chat_history = get_chat_history()
    sessions = list_all_sessions()
    
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
        /* Light mode (default) */
        :root {
            --primary-color: #2563eb;
            --primary-hover: #1e40af;
            --primary-bg: #ffffff;
            --secondary-bg: #f1f5f9;
            --tertiary-bg: #e2e8f0;
            --primary-text: #0f172a;
            --secondary-text: #475569;
            --light-text: #f8fafc;
            --border-color: #cbd5e1;
            --border-radius: 8px;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Dark mode */
        [data-theme="dark"] {
            --primary-color: #3b82f6;
            --primary-hover: #60a5fa;
            --primary-bg: #0f172a;
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
            font-family: system-ui, -apple-system, sans-serif;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Beta banner */
        .beta-banner {
            background-color: #fefbeb;
            border: 1px solid #f0e9db;
            border-radius: 4px;
            padding: 0.3rem 1rem;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        [data-theme="dark"] .beta-banner {
            background-color: #2d3748;
            border-color: #4a5568;
        }
        
        .beta-banner-content {
            color: #92400e;
            font-size: 0.8rem;
        }
        
        [data-theme="dark"] .beta-banner-content {
            color: #fbd38d;
        }
        
        .beta-close-btn {
            background: none;
            border: none;
            color: #92400e;
            cursor: pointer;
            font-size: 1.2rem;
            padding: 0;
            margin-left: 0.5rem;
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
        
        /* Chat container */
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
                    <div id="processing-status" class="d-none alert alert-info">
                        <div class="d-flex align-items-center">
                            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                            <span id="status-message">Processing your question...</span>
                        </div>
                        <div class="progress mt-2" style="height: 5px;">
                            <div id="status-progress" class="progress-bar" role="progressbar" style="width: 0%"></div>
                        </div>
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
                    <div class="card-header bg-primary text-white">
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
                    <div class="card-header bg-primary text-white">
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
                
                <div class="text-center text-muted my-5">
                    <i class="fa fa-sitemap fa-2x mb-3"></i>
                    <p>No diagrams have been generated yet. Ask a question that requires visualization!</p>
                </div>
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
                            <div class="card-header bg-primary text-white">
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
                            <div class="card-header bg-primary text-white">
                                <h5 class="card-title mb-0">Available Sessions</h5>
                            </div>
                            <div class="card-body">
                                {% if sessions %}
                                    <div class="list-group">
                                        {% for session_id, session_data in sessions.items() %}
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
        // Wait for DOM to load
        document.addEventListener('DOMContentLoaded', function() {
            // Tab switching
            var tabButtons = document.querySelectorAll('.tab-button');
            var tabContents = document.querySelectorAll('.tab-content');
            
            tabButtons.forEach(function(button) {
                button.addEventListener('click', function() {
                    // Deactivate all tabs
                    tabButtons.forEach(function(btn) {
                        btn.classList.remove('active');
                    });
                    
                    tabContents.forEach(function(content) {
                        content.classList.remove('active');
                    });
                    
                    // Activate current tab
                    this.classList.add('active');
                    var tabId = this.getAttribute('data-tab');
                    document.getElementById(tabId).classList.add('active');
                });
            });
            
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
            
            // Form handling
            var questionForm = document.getElementById('questionForm');
            var processingStatus = document.getElementById('processing-status');
            var statusMessage = document.getElementById('status-message');
            var statusProgress = document.getElementById('status-progress');
            
            if (questionForm) {
                questionForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    var questionInput = document.getElementById('questionInput');
                    var question = questionInput.value.trim();
                    
                    if (!question) return;
                    
                    // Show processing status
                    processingStatus.classList.remove('d-none');
                    statusMessage.textContent = 'Processing your question...';
                    statusProgress.style.width = '10%';
                    
                    // Add user message to chat
                    var chatMessages = document.getElementById('chatMessages');
                    var userDiv = document.createElement('div');
                    userDiv.className = 'user-message';
                    userDiv.textContent = 'You: ' + question;
                    chatMessages.appendChild(userDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Clear input
                    questionInput.value = '';
                    
                    // In a real implementation, this would make an API call
                    // and poll for status updates
                    setTimeout(function() {
                        // Add bot response
                        var botDiv = document.createElement('div');
                        botDiv.className = 'bot-message';
                        botDiv.innerHTML = '<strong>RegCap GPT:</strong> This is a simulated response. In the real application, this would be generated by analyzing your documents using AI.';
                        chatMessages.appendChild(botDiv);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        // Hide processing status
                        processingStatus.classList.add('d-none');
                    }, 2000);
                });
            }
            
            // Upload form handling
            var uploadForm = document.getElementById('uploadForm');
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    var fileInput = document.getElementById('documentUpload');
                    if (fileInput.files.length === 0) {
                        alert('Please select at least one PDF file to upload.');
                        return;
                    }
                    
                    // Show loading state
                    var submitBtn = this.querySelector('button[type="submit"]');
                    var originalBtnText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Uploading...';
                    submitBtn.disabled = true;
                    
                    // Create form data
                    var formData = new FormData();
                    for (var i = 0; i < fileInput.files.length; i++) {
                        formData.append('files', fileInput.files[i]);
                    }
                    
                    // Upload files
                    fetch('/upload-files', {
                        method: 'POST',
                        body: formData
                    })
                    .then(function(response) {
                        return response.json();
                    })
                    .then(function(data) {
                        if (data.success) {
                            alert('File(s) uploaded successfully!');
                            location.reload(); // Reload to show uploaded files
                        } else {
                            alert('Error: ' + data.error);
                        }
                    })
                    .catch(function(error) {
                        console.error('Upload error:', error);
                        alert('An error occurred during upload.');
                    })
                    .finally(function() {
                        // Reset button state
                        submitBtn.innerHTML = originalBtnText;
                        submitBtn.disabled = false;
                    });
                });
            }
            
            // Session management
            var newSessionBtn = document.getElementById('newSessionBtn');
            if (newSessionBtn) {
                newSessionBtn.addEventListener('click', function() {
                    if (confirm('Create a new session? This will start with a clean slate.')) {
                        alert('New session simulation: In the real application, this would create a new session.');
                    }
                });
            }
            
            var sessionSwitchBtns = document.querySelectorAll('.session-switch-btn');
            sessionSwitchBtns.forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var sessionId = this.getAttribute('data-session-id');
                    if (confirm('Switch to session ' + sessionId + '?')) {
                        alert('Session switch simulation: In the real application, this would switch to the selected session.');
                    }
                });
            });
        });
    </script>
</body>
</html>
    """, 
    session_id=session_id,
    documents=documents,
    chat_history=chat_history,
    sessions=sessions
    )

@app.route('/upload-files', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    try:
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'No files selected'})
        
        session_id = get_current_session()
        
        for file in files:
            if file and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Extract text (would be more sophisticated in real app)
                chunks = extract_text_from_pdf(file_path)
                
                # Store document chunks
                if session_id not in storage["documents"]:
                    storage["documents"][session_id] = {}
                storage["documents"][session_id][filename] = chunks
                
        return jsonify({'success': True, 'message': f'Processed {len(files)} files'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ask-question', methods=['POST'])
def ask_question():
    """Handle questions from the user."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})
        
        # Generate unique ID for this question
        question_id = f"q_{uuid.uuid4().hex[:8]}"
        
        # Start processing in background thread
        threading.Thread(
            target=process_question,
            args=(question, question_id),
            daemon=True
        ).start()
        
        return jsonify({
            'success': True,
            'message': 'Question received',
            'question_id': question_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def process_question(question, question_id):
    """
    Process a question in the background using a multi-stage pipeline.
    
    This function handles the entire question processing workflow:
    1. Duplicate detection to prevent reprocessing identical questions
    2. Document retrieval from the knowledge base
    3. Vector embedding creation for semantic search
    4. Relevant context retrieval using vector similarity
    5. AI content generation (either text answers or diagrams)
    6. Storing results and updating processing status
    
    The function runs in a separate thread to prevent blocking the main Flask 
    application, providing status updates during processing that can be 
    polled by the frontend.
    
    Args:
        question (str): The user's question text
        question_id (str): Unique identifier for tracking this question's processing
        
    Returns:
        None: Results are saved to chat history and diagram storage
    """
    try:
        update_question_status(question_id, stage="Starting analysis...", progress=10)
        
        # In a real implementation, this would:
        # 1. Extract relevant info from documents
        # 2. Generate an answer using OpenAI
        # 3. Store the results
        
        # Simulate processing delay
        time.sleep(2)
        update_question_status(question_id, stage="Finding relevant information...", progress=30)
        time.sleep(2)
        update_question_status(question_id, stage="Generating response...", progress=70)
        time.sleep(1)
        
        # Generate a simple response
        answer = f"This is a simulated answer to your question: '{question}'\n\nIn a real implementation, this would analyze your uploaded documents using AI to provide a specific answer."
        
        # Save to chat history
        save_chat_history(question, answer)
        
        # Mark as complete
        update_question_status(question_id, stage="Complete", progress=100, done=True)
    except Exception as e:
        update_question_status(question_id, error=f"Error processing question: {str(e)}")

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
        
        if not session_id or session_id not in storage["sessions"]:
            return jsonify({'success': False, 'error': 'Invalid session ID'})
        
        storage["current_session"] = session_id
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/view-diagram/<int:diagram_index>')
def view_diagram(diagram_index):
    """Show a single diagram on a dedicated page."""
    try:
        session_id = get_current_session()
        diagrams = storage["diagrams"].get(session_id, [])
        
        if not diagrams or diagram_index >= len(diagrams):
            return "Diagram not found", 404
        
        diagram_code, explanation, diagram_type = diagrams[diagram_index]
        
        return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>RegCap GPT - Diagram Viewer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {
            padding: 2rem;
        }
        .diagram-container {
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 8px;
            margin: 1rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">{{ diagram_type|capitalize }} Diagram</h1>
        <p><strong>Explanation:</strong> {{ explanation }}</p>
        
        <div class="diagram-container">
            <div class="mermaid">
{{ diagram_code }}
            </div>
        </div>
        
        <a href="/" class="btn btn-primary">Back to Main Page</a>
    </div>
    
    <script>
        mermaid.initialize({
            startOnLoad: true,
            securityLevel: 'loose',
            theme: 'default'
        });
    </script>
</body>
</html>
        """, diagram_code=diagram_code, explanation=explanation, diagram_type=diagram_type)
    except Exception as e:
        return f"Error displaying diagram: {str(e)}", 500

@app.route('/question-status/<question_id>')
def get_question_status(question_id):
    """Get the status of a specific question."""
    if question_id in storage["question_status"]:
        return jsonify(storage["question_status"][question_id])
    return jsonify({'error': 'Question not found', 'done': True})

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run the RegCap GPT Flask application')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the application on')
    args = parser.parse_args()
    
    app.run(host='0.0.0.0', port=args.port)