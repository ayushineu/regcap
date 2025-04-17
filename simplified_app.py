from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
import os
import time
import pickle
import base64
import uuid
import json
import PyPDF2
import threading
import openai
import numpy as np
import faiss
import re
from werkzeug.utils import secure_filename
from fix_mermaid import fix_mermaid_syntax
from flask_app import (
    SimpleStorage, get_current_session, create_new_session, 
    encode_for_storage, decode_from_storage, extract_text_from_pdf,
    save_document_chunks, get_document_chunks, get_all_document_chunks,
    get_embedding, create_vector_store, get_similar_chunks,
    generate_answer, generate_diagram, detect_diagram_request,
    save_chat_history, get_chat_history, save_diagram, get_diagrams,
    list_all_sessions, log_message, update_question_status
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize OpenAI client
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Using the imported fix_mermaid_syntax function from fix_mermaid.py

@app.route('/')
def index():
    """Render the main application page."""
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
        
        /* Add styles for notification dot */
        .diagram-notification {
            position: relative;
        }
        
        .diagram-notification .dot {
            position: absolute;
            top: 0;
            right: 0;
            width: 10px;
            height: 10px;
            background-color: #ff9900;
            border-radius: 50%;
            display: none;
        }
        
        /* Improved diagram styling */
        .diagram-container {
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            margin: 10px 0;
            overflow-x: auto;
            background-color: var(--secondary-bg);
        }
        
        .svg-container {
            width: 100%;
            overflow-x: auto;
            padding: 10px;
        }
        
        .error-container {
            margin: 10px 0;
            padding: 15px;
            background-color: #fff3cd;
            border-radius: 5px;
            border: 1px solid #ffecb5;
            display: none;
        }
        
        .mermaid svg {
            max-width: 100%;
            height: auto;
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
                <button class="tab-button diagram-notification" data-tab="diagrams">
                    Diagrams
                    <span class="dot" id="diagramsNotification"></span>
                </button>
                <button class="tab-button" data-tab="sessions">Sessions</button>
            </div>
            
            <div id="chat" class="tab-content active">
                <h2>Chat</h2>
                <div class="chat-container" id="chatMessages">
                    {% if chat_history %}
                        {% for question, answer in chat_history %}
                            <div class="user-message">
                                <strong>You:</strong> {{ question }}
                            </div>
                            <div class="bot-message">
                                <strong>Bot:</strong> {{ answer|safe }}
                            </div>
                        {% endfor %}
                    {% else %}
                        <div class="bot-message">
                            <strong>Bot:</strong> Welcome to RegCap GPT! I'm your regulatory intelligence assistant. Upload regulatory documents and ask me questions about them.
                        </div>
                    {% endif %}
                </div>
                <form id="question-form" action="/ask" method="post">
                    <div class="mb-3">
                        <label for="question" class="form-label">Your Question:</label>
                        <textarea class="form-control" id="question" name="question" rows="3" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary" id="askButton">Ask</button>
                    <div id="processingIndicator" style="display:none; margin-top: 15px;" class="alert alert-info">
                        <div class="d-flex align-items-center">
                            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                            <span class="processing">Processing your question...</span>
                        </div>
                    </div>
                    <div id="lastQuestion" style="display:none; margin-top: 15px;" class="alert alert-secondary">
                        <strong>Last question: </strong><span id="lastQuestionText"></span>
                    </div>
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
                        <div class="card mb-5">
                            <div class="card-header">
                                <h3>{{ diagram_type|capitalize }} Diagram</h3>
                            </div>
                            <div class="card-body">
                                <p><strong>Explanation:</strong> {{ explanation }}</p>
                                
                                <!-- Diagram Tabs -->
                                <div class="tabs diagram-tabs mt-3">
                                    <div class="tab-item active" data-parent-index="{{ loop.index0 }}" data-tab="simplified">Simplified Diagram</div>
                                    <div class="tab-item" data-parent-index="{{ loop.index0 }}" data-tab="rawcode">Raw Code</div>
                                    <div class="tab-item" data-parent-index="{{ loop.index0 }}" data-tab="fullpage">Full Page View</div>
                                </div>
                                
                                <!-- Tab Contents -->
                                <div id="simplified-{{ loop.index0 }}" class="tab-content active">
                                    <div class="diagram-container">
                                        <div class="mermaid diagram-display">{{ diagram_code }}</div>
                                    </div>
                                </div>
                                
                                <div id="rawcode-{{ loop.index0 }}" class="tab-content">
                                    <div class="code-container p-3 bg-light border rounded">
                                        <pre class="m-0">{{ diagram_code }}</pre>
                                    </div>
                                </div>
                                
                                <div id="fullpage-{{ loop.index0 }}" class="tab-content">
                                    <div class="alert alert-info">
                                        <i class="fa fa-info-circle"></i> For better diagram viewing with more options, click the button below to open in a dedicated page.
                                    </div>
                                    <a href="/view_diagram/{{ loop.index0 }}" class="btn btn-primary" target="_blank">
                                        <i class="fa fa-external-link"></i> Open Full Page View
                                    </a>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>No diagrams generated yet. Ask a question that requires visualization.</p>
                    <div class="alert alert-secondary">
                        <h4>How to get diagrams:</h4>
                        <p>Try asking questions like:</p>
                        <ul>
                            <li>"Create a flowchart of the workflow described in the document"</li>
                            <li>"Show me a diagram of the process"</li>
                            <li>"Can you visualize the relationship between the concepts in this document?"</li>
                        </ul>
                    </div>
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
        // Very basic script for tab switching
        document.addEventListener('DOMContentLoaded', function() {
            // Basic tab switching
            var tabButtons = document.querySelectorAll('.tab-button');
            for (var i = 0; i < tabButtons.length; i++) {
                tabButtons[i].onclick = function() {
                    var tabId = this.getAttribute('data-tab');
                    
                    // Hide all tabs
                    var tabContents = document.querySelectorAll('.tab-content');
                    for (var j = 0; j < tabContents.length; j++) {
                        tabContents[j].classList.remove('active');
                    }
                    
                    // Remove active class from all buttons
                    for (var j = 0; j < tabButtons.length; j++) {
                        tabButtons[j].classList.remove('active');
                    }
                    
                    // Show selected tab
                    document.getElementById(tabId).classList.add('active');
                    this.classList.add('active');
                    
                    // Diagram tab special handling
                    if (tabId === 'diagrams') {
                        var notificationDot = document.getElementById('diagramsNotification');
                        if (notificationDot) {
                            notificationDot.style.display = 'none';
                        }
                        renderAllDiagrams();
                    }
                };
            }
            
            // Dark mode toggle
            var darkModeToggle = document.getElementById('darkModeToggle');
            if (darkModeToggle) {
                // Check saved preference
                var savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'dark') {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    darkModeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                }
                
                // Toggle theme on click
                darkModeToggle.onclick = function() {
                    if (document.documentElement.getAttribute('data-theme') === 'dark') {
                        document.documentElement.removeAttribute('data-theme');
                        localStorage.setItem('theme', 'light');
                        darkModeToggle.innerHTML = '<i class="fa fa-moon-o"></i> Dark Mode';
                    } else {
                        document.documentElement.setAttribute('data-theme', 'dark');
                        localStorage.setItem('theme', 'dark');
                        darkModeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                    }
                };
            }
            
            // Question form handling
            var questionForm = document.getElementById('question-form');
            if (questionForm) {
                questionForm.onsubmit = function(e) {
                    e.preventDefault();
                    
                    var question = document.getElementById('question').value.trim();
                    if (!question) return;
                    
                    // Disable submit button
                    var submitButton = this.querySelector('button[type="submit"]');
                    submitButton.disabled = true;
                    
                    // Show processing indicator
                    var processingIndicator = document.getElementById('processingIndicator');
                    if (processingIndicator) {
                        processingIndicator.style.display = 'block';
                    }
                    
                    // Save the question text to display if page reloads
                    localStorage.setItem('lastQuestion', question);
                    
                    // Show the last question indicator
                    var lastQuestion = document.getElementById('lastQuestion');
                    var lastQuestionText = document.getElementById('lastQuestionText');
                    if (lastQuestion && lastQuestionText) {
                        lastQuestionText.textContent = question;
                        lastQuestion.style.display = 'block';
                    }
                    
                    // Add user message to chat
                    var chatContainer = document.getElementById('chatMessages');
                    var userMessage = document.createElement('div');
                    userMessage.className = 'user-message';
                    userMessage.innerHTML = '<strong>You:</strong> ' + question;
                    chatContainer.appendChild(userMessage);
                    
                    // Add bot response placeholder
                    var botMessage = document.createElement('div');
                    botMessage.className = 'bot-message';
                    botMessage.innerHTML = '<strong>Bot:</strong> <span class="processing">Processing your question... <div class="spinner-border spinner-border-sm" role="status"></div></span>';
                    chatContainer.appendChild(botMessage);
                    
                    // Auto-scroll to bottom
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    
                    // Submit the question
                    var formData = new FormData();
                    formData.append('question', question);
                    
                    fetch('/ask', {
                        method: 'POST',
                        body: formData
                    })
                    .then(function(response) {
                        return response.json();
                    })
                    .then(function(data) {
                        if (data.success) {
                            // Show processing stages with longer timeouts
                            var processingSpan = document.querySelector('.processing');
                            if (processingSpan) {
                                // Stage 1
                                setTimeout(function() {
                                    processingSpan.innerHTML = "Finding information in documents... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                }, 2000);
                                
                                // Stage 2
                                setTimeout(function() {
                                    processingSpan.innerHTML = "Creating vector embeddings... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                }, 5000);
                                
                                // Stage 3
                                setTimeout(function() {
                                    processingSpan.innerHTML = "Generating answer... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                }, 8000);
                            }
                            
                            // Wait longer before reloading
                            setTimeout(function() {
                                window.location.reload();
                            }, 15000);
                        } else {
                            alert('Error: ' + (data.error || 'Unknown error'));
                            submitButton.disabled = false;
                        }
                    })
                    .catch(function(error) {
                        console.error('Error:', error);
                        alert('Error processing request');
                        submitButton.disabled = false;
                    });
                    
                    // Clear the input
                    document.getElementById('question').value = '';
                };
            }
            
            // Session buttons
            var createSessionBtn = document.getElementById('createNewSession');
            if (createSessionBtn) {
                createSessionBtn.onclick = function() {
                    fetch('/new_session', {
                        method: 'POST'
                    })
                    .then(function(response) {
                        if (response.ok) {
                            window.location.reload();
                        }
                    });
                };
            }
            
            var switchButtons = document.querySelectorAll('.switch-session');
            for (var i = 0; i < switchButtons.length; i++) {
                switchButtons[i].onclick = function() {
                    var sessionId = this.getAttribute('data-session-id');
                    var formData = new FormData();
                    formData.append('session_id', sessionId);
                    
                    fetch('/switch_session', {
                        method: 'POST',
                        body: formData
                    })
                    .then(function(response) {
                        if (response.ok) {
                            window.location.reload();
                        }
                    });
                };
            }
            
            // Diagram rendering 
            function renderAllDiagrams() {
                var diagrams = document.querySelectorAll('.mermaid');
                for (var i = 0; i < diagrams.length; i++) {
                    try {
                        mermaid.init(undefined, diagrams[i]);
                    } catch (e) {
                        console.error('Error rendering diagram:', e);
                    }
                }
            }
            
            // Diagram tabs handling (the tabs within the diagrams tab)
            var diagramTabItems = document.querySelectorAll('.diagram-tabs .tab-item');
            for (var i = 0; i < diagramTabItems.length; i++) {
                diagramTabItems[i].addEventListener('click', function() {
                    var tabId = this.getAttribute('data-tab');
                    var parentIndex = this.getAttribute('data-parent-index');
                    
                    // Hide all tab contents for this diagram
                    var parentDiagramCard = this.closest('.card');
                    var tabContents = parentDiagramCard.querySelectorAll('.tab-content');
                    tabContents.forEach(function(content) {
                        content.classList.remove('active');
                    });
                    
                    // Deactivate all tabs for this diagram
                    var tabItems = parentDiagramCard.querySelectorAll('.tab-item');
                    tabItems.forEach(function(item) {
                        item.classList.remove('active');
                    });
                    
                    // Activate clicked tab and its content
                    this.classList.add('active');
                    parentDiagramCard.querySelector('#' + tabId + '-' + parentIndex).classList.add('active');
                    
                    // Re-render mermaid if needed
                    if (tabId === 'simplified') {
                        try {
                            var diagram = parentDiagramCard.querySelector('#simplified-' + parentIndex + ' .mermaid');
                            if (diagram) {
                                mermaid.init(undefined, diagram);
                            }
                        } catch (e) {
                            console.error('Error rendering diagram in tab switch:', e);
                        }
                    }
                });
            }
            
            // Initialize mermaid for diagrams
            if (typeof mermaid !== 'undefined') {
                mermaid.initialize({ 
                    startOnLoad: false,  // Important: we'll manually render diagrams
                    securityLevel: 'loose',
                    logLevel: 'error',
                    theme: 'default',
                    flowchart: {
                        htmlLabels: true,
                        useMaxWidth: true,
                        curve: 'linear'  // Simpler edges for better compatibility
                    }
                });
                
                // Check if we have diagrams
                var hasDiagrams = document.querySelectorAll('.mermaid').length > 0;
                if (hasDiagrams) {
                    var notificationDot = document.getElementById('diagramsNotification');
                    if (notificationDot) {
                        notificationDot.style.display = 'block';
                    }
                }
            }
            
            // Check for last question in localStorage
            var lastQuestion = localStorage.getItem('lastQuestion');
            if (lastQuestion) {
                var lastQuestionDiv = document.getElementById('lastQuestion');
                var lastQuestionText = document.getElementById('lastQuestionText');
                if (lastQuestionDiv && lastQuestionText) {
                    lastQuestionText.textContent = lastQuestion;
                    lastQuestionDiv.style.display = 'block';
                }
                
                // Clear it after showing (it will be set again when submitting a new question)
                localStorage.removeItem('lastQuestion');
            }
        });
    </script>
</body>
</html>
    """, documents=documents, chat_history=chat_history, diagrams=diagrams, session_id=session_id, sessions=sessions)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'document' not in request.files:
        return redirect(url_for('index'))
    
    files = request.files.getlist('document')
    
    for file in files:
        if file.filename == '':
            continue
        
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            temp_path = os.path.join('/tmp', filename)
            file.save(temp_path)
            
            try:
                # Extract text and create chunks
                text_chunks = extract_text_from_pdf(temp_path)
                if text_chunks:
                    # Save chunks to storage
                    save_document_chunks(filename, text_chunks)
                
                # Clean up temp file
                os.remove(temp_path)
            except Exception as e:
                log_message(f"Error processing PDF {filename}: {str(e)}")
    
    return redirect(url_for('index'))

@app.route('/ask', methods=['POST'])
def ask_question():
    """Handle questions from the user."""
    question = request.form.get('question', '').strip()
    
    if not question:
        return jsonify({"success": False, "error": "No question provided"})
    
    # Generate a unique ID for this question
    question_id = str(uuid.uuid4())
    
    # Create thread to process question in background
    processing_thread = threading.Thread(
        target=process_question,
        args=(question, question_id)
    )
    processing_thread.daemon = True
    processing_thread.start()
    
    # AJAX handling - always return JSON for simplicity
    return jsonify({"success": True, "question_id": question_id})

def process_question(question, question_id):
    """Process a question in the background."""
    try:
        # Check if we already have this question in history to avoid duplicates
        current_history = get_chat_history()
        for q, _ in current_history:
            # Use string similarity to detect duplicate questions
            if question.lower().strip() == q.lower().strip():
                print(f"Duplicate question detected: '{question}' - skipping processing")
                return
        
        # Update status to indicate we're starting
        update_question_status(question_id, stage="Starting", progress=0)
        
        # Get all document chunks
        chunks = get_all_document_chunks()
        if not chunks:
            answer = "Please upload some documents first. I don't have any knowledge base to work with yet."
            save_chat_history(question, answer)
            update_question_status(question_id, stage="Complete", progress=100, done=True)
            return
        
        # Check if it's a diagram request
        is_diagram_request, diagram_type = detect_diagram_request(question)
        
        # Create vector store
        update_question_status(question_id, stage="Creating vector store", progress=20)
        vector_store = create_vector_store(chunks)
        
        # Get similar chunks
        update_question_status(question_id, stage="Finding relevant information", progress=40)
        similar_chunks = get_similar_chunks(question, vector_store)
        
        # Generate answer or diagram
        if is_diagram_request:
            # Default to flowchart if diagram_type is None
            actual_diagram_type = diagram_type if diagram_type else "flowchart"
            update_question_status(question_id, stage=f"Generating {actual_diagram_type} diagram", progress=60)
            
            try:
                success, result = generate_diagram(question, similar_chunks, actual_diagram_type)
                
                if success:
                    diagram_code, explanation = result
                    # Fix any Mermaid syntax issues
                    diagram_code = fix_mermaid_syntax(diagram_code, actual_diagram_type)
                    answer = f"I've created a {actual_diagram_type} diagram based on your request. Please click on the \"Diagrams\" tab above to view it."
                    
                    # Save the diagram
                    save_diagram(diagram_code, explanation, actual_diagram_type)
                else:
                    # Handle error case
                    answer = f"I couldn't generate a diagram: {result}"
            except Exception as e:
                # Handle any errors during diagram generation
                error_msg = str(e)
                log_message(f"Error generating diagram: {error_msg}")
                answer = f"I had trouble creating the diagram. Error: {error_msg}"
        else:
            update_question_status(question_id, stage="Generating answer", progress=60)
            answer = generate_answer(question, similar_chunks)
        
        # Save to chat history
        update_question_status(question_id, stage="Saving results", progress=80)
        save_chat_history(question, answer)
        
        # Mark as complete
        update_question_status(question_id, stage="Complete", progress=100, done=True)
        
    except Exception as e:
        error_msg = str(e)
        log_message(f"Error processing question: {error_msg}")
        update_question_status(question_id, stage="Error", error=error_msg, done=True)
        
        # Save error to chat history
        save_chat_history(question, f"Sorry, I encountered an error: {error_msg}")

@app.route('/new_session', methods=['POST'])
def new_session():
    """Create a new session."""
    create_new_session()
    return redirect(url_for('index'))

@app.route('/switch_session', methods=['POST'])
def switch_session():
    """Switch to a different session."""
    session_id = request.form.get('session_id')
    if session_id:
        session['current_session'] = session_id
    return redirect(url_for('index'))

@app.route('/view_diagram/<int:diagram_index>')
def view_diagram(diagram_index):
    """Show a single diagram on a dedicated page."""
    raw_diagrams = get_diagrams()
    
    if not raw_diagrams:
        return redirect(url_for('index'))
    
    # De-duplicate diagrams just like in the index route
    seen_diagrams = set()
    unique_diagrams = []
    
    for diagram_code, explanation, diagram_type in raw_diagrams:
        diagram_id = f"{explanation}-{diagram_type}"
        if diagram_id not in seen_diagrams:
            seen_diagrams.add(diagram_id)
            unique_diagrams.append((diagram_code, explanation, diagram_type))
    
    if diagram_index >= len(unique_diagrams):
        return redirect(url_for('index'))
    
    diagram_code, explanation, diagram_type = unique_diagrams[diagram_index]
    
    # Create a simplified version of the diagram
    # Use extremely simple syntax that works in any mermaid version
    if diagram_type == "flowchart":
        simplified_code = """
graph TD
    A(Start) --> B(Identify Activities)
    B --> C(Involve Business Experts)
    C --> D(Engage Technical Experts)
    D --> E(Develop Data Dictionary)
    E --> F(Define Message Models)
    F --> G(Complete & Register)
    G --> H(End)
"""
    elif diagram_type == "sequence":
        simplified_code = """
sequenceDiagram
    participant User
    participant System
    User->>System: Submit Request
    System->>System: Process Request
    System->>User: Return Response
"""
    else:  # Default to flowchart
        simplified_code = """
graph TD
    A(ISO 20022 Workflow Process)
    A --> B(Identify Activities)
    B --> C(Involve Business Experts)
    C --> D(Engage Technical Experts)
    D --> E(Complete & Register)
"""
    
    # Apply extra fixes for complex diagrams
    diagram_code = fix_mermaid_syntax(diagram_code, diagram_type)
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ diagram_type|capitalize }} Diagram</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@9.1.7/dist/mermaid.min.js"></script>
    <style>
        body {
            padding: 40px;
            max-width: 1200px;
            margin: 0 auto;
            font-family: Arial, sans-serif;
        }
        h1 {
            margin-bottom: 30px;
        }
        .explanation {
            margin: 20px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .diagram-container {
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 20px 0;
            overflow-x: auto;
        }
        .mermaid {
            font-size: 16px;
            line-height: 1.5;
        }
        .error-container {
            margin: 20px 0;
            padding: 15px;
            background-color: #fff3cd;
            border-radius: 5px;
            border: 1px solid #ffecb5;
        }
        .simplification-notice {
            margin: 20px 0;
            padding: 15px;
            background-color: #e7f3fe;
            border-radius: 5px;
            border: 1px solid #b6d4fe;
        }
        .svg-container {
            width: 100%;
            overflow-x: auto;
            padding: 10px;
        }
        pre {
            white-space: pre-wrap;
        }
        .tabs {
            display: flex;
            margin-bottom: 0;
            padding-left: 0;
            list-style: none;
            border-bottom: 1px solid #dee2e6;
        }
        .tab-item {
            margin-bottom: -1px;
            padding: 0.5rem 1rem;
            cursor: pointer;
            background-color: #f8f9fa;
            border: 1px solid transparent;
            border-top-left-radius: 0.25rem;
            border-top-right-radius: 0.25rem;
        }
        .tab-item.active {
            color: #495057;
            background-color: #fff;
            border-color: #dee2e6 #dee2e6 #fff;
        }
        .tab-content {
            display: none;
            padding: 20px;
            border: 1px solid #dee2e6;
            border-top: none;
        }
        .tab-content.active {
            display: block;
        }
        #simplified-diagram {
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>{{ diagram_type|capitalize }} Diagram</h1>
    
    <div class="explanation">
        <h3>Explanation</h3>
        <p>{{ explanation }}</p>
    </div>

    <div class="tabs">
        <div class="tab-item active" data-tab="generated">Generated Diagram</div>
        <div class="tab-item" data-tab="simplified">Simplified Diagram</div>
        <div class="tab-item" data-tab="code">Raw Code</div>
    </div>
    
    <div id="generated" class="tab-content active">
        <div class="diagram-container">
            <div id="generated-diagram" class="mermaid">{{ diagram_code }}</div>
        </div>
    </div>
    
    <div id="simplified" class="tab-content">
        <div class="simplification-notice">
            This is a simplified version of the diagram to ensure proper rendering.
        </div>
        <div class="diagram-container">
            <div id="simplified-diagram" class="mermaid">{{ simplified_code }}</div>
        </div>
    </div>
    
    <div id="code" class="tab-content">
        <div class="error-container">
            <h4>Diagram Code</h4>
            <p>Here's the raw diagram code if you'd like to use it in another tool:</p>
            <pre id="raw-code" class="border p-3 bg-light">{{ diagram_code }}</pre>
        </div>
    </div>
    
    <div class="mt-4">
        <a href="/" class="btn btn-primary">Back to Main App</a>
    </div>
    
    <script>
        // Configure mermaid with the most permissive, basic settings
        mermaid.initialize({
            startOnLoad: false,  // Important: manually control initialization
            securityLevel: 'loose',
            logLevel: 'error',
            theme: 'default',
            flowchart: {
                htmlLabels: true,
                useMaxWidth: true,
                curve: 'linear'  // Simpler edges for better compatibility
            }
        });
        
        document.addEventListener('DOMContentLoaded', function() {
            // Tab switching
            var tabItems = document.querySelectorAll('.tab-item');
            for (var i = 0; i < tabItems.length; i++) {
                tabItems[i].addEventListener('click', function() {
                    // Hide all tab contents
                    document.querySelectorAll('.tab-content').forEach(function(content) {
                        content.classList.remove('active');
                    });
                    
                    // Deactivate all tabs
                    document.querySelectorAll('.tab-item').forEach(function(tab) {
                        tab.classList.remove('active');
                    });
                    
                    // Activate clicked tab and its content
                    this.classList.add('active');
                    var tabId = this.getAttribute('data-tab');
                    document.getElementById(tabId).classList.add('active');
                });
            }
            
            // Always render the simplified diagram first as it's more reliable
            var simpleDiagram = document.getElementById('simplified-diagram');
            if (simpleDiagram) {
                try {
                    mermaid.render('simplified-svg', simpleDiagram.textContent, function(svgCode) {
                        simpleDiagram.innerHTML = svgCode;
                    });
                } catch (e) {
                    console.error('Error rendering simplified diagram:', e);
                    // If even simplified fails, just show an error message
                    simpleDiagram.innerHTML = '<div class="alert alert-danger">Unable to render any diagram. Please view the raw code.</div>';
                }
            }
            
            // Try to render the generated diagram with a direct fallback
            var generatedDiagram = document.getElementById('generated-diagram');
            if (generatedDiagram) {
                try {
                    mermaid.render('generated-svg', generatedDiagram.textContent, function(svgCode) {
                        generatedDiagram.innerHTML = svgCode;
                    });
                } catch (e) {
                    console.error('Error rendering generated diagram:', e);
                    // If failed, auto-switch to simplified tab
                    var simplifiedTab = document.querySelector('[data-tab="simplified"]');
                    if (simplifiedTab) {
                        setTimeout(function() {
                            simplifiedTab.click();
                            // Also show a notice in the generated tab
                            generatedDiagram.innerHTML = '<div class="alert alert-warning">The generated diagram had syntax errors and could not be displayed. Switched to simplified view.</div>';
                        }, 100);
                    }
                }
            }
        });
    </script>
</body>
</html>
    """, 
    diagram_code=diagram_code, 
    explanation=explanation, 
    diagram_type=diagram_type, 
    simplified_code=simplified_code)

@app.route('/get_question_status/<question_id>')
def get_question_status(question_id):
    """Get the status of a specific question."""
    storage = SimpleStorage()
    status_key = f"question_status:{question_id}"
    
    if status_key in storage:
        return jsonify(storage[status_key])
    else:
        return jsonify({"error": "Question not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)