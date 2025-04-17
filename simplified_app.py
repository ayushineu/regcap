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

def fix_mermaid_syntax(diagram_code: str, diagram_type: str = "flowchart") -> str:
    """Fix common Mermaid syntax issues to ensure proper rendering."""
    if not diagram_code:
        # Default empty diagram based on type
        if diagram_type == "flowchart":
            return "flowchart TD\nA[Empty Diagram]"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        elif diagram_type == "mindmap":
            return "mindmap\nroot(Empty Diagram)"
        else:
            return "flowchart TD\nA[Empty Diagram]"
    
    # Clean up whitespace and control characters
    diagram_code = diagram_code.strip()
    diagram_code = re.sub(r'[\x00-\x1F\x7F]', '', diagram_code)  # Remove control characters
    
    # Remove markdown code block syntax if present
    if "```" in diagram_code:
        # Extract content between ```mermaid and ```
        if "```mermaid" in diagram_code:
            match = re.search(r'```mermaid\n(.*?)```', diagram_code, re.DOTALL)
            if match:
                diagram_code = match.group(1).strip()
        else:
            # Extract content between ``` and ```
            match = re.search(r'```\n?(.*?)```', diagram_code, re.DOTALL)
            if match:
                diagram_code = match.group(1).strip()
    
    # Normalize line endings
    diagram_code = diagram_code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines for processing
    lines = diagram_code.split('\n')
    cleaned_lines = []
    
    # Process each line
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        # Remove excessive spaces
        line = re.sub(r'\s+', ' ', line.strip())
        cleaned_lines.append(line)
    
    if not cleaned_lines:
        # If all lines were removed, return a default diagram
        if diagram_type == "flowchart":
            return "flowchart TD\nA[Empty Diagram]"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        elif diagram_type == "mindmap":
            return "mindmap\nroot(Empty Diagram)"
        else:
            return "flowchart TD\nA[Empty Diagram]"
    
    # Rebuild the diagram code
    diagram_code = '\n'.join(cleaned_lines)
    
    # Ensure proper diagram type declaration
    if diagram_type == "flowchart":
        if not (diagram_code.startswith("flowchart") or diagram_code.startswith("graph")):
            diagram_code = "flowchart TD\n" + diagram_code
        # Convert 'graph TD' to 'flowchart TD' for consistency
        elif diagram_code.startswith("graph"):
            direction = "TD"
            if "graph LR" in diagram_code:
                direction = "LR"
            elif "graph RL" in diagram_code:
                direction = "RL"
            elif "graph BT" in diagram_code:
                direction = "BT"
            diagram_code = diagram_code.replace(f"graph {direction}", f"flowchart {direction}", 1)
    elif diagram_type == "sequence" and not diagram_code.startswith("sequenceDiagram"):
        diagram_code = "sequenceDiagram\n" + diagram_code
    elif diagram_type == "mindmap" and not diagram_code.startswith("mindmap"):
        diagram_code = "mindmap\n" + diagram_code
    
    # Fix common syntax errors
    # Fix missing brackets in node definitions
    diagram_code = re.sub(r'(\s)(\w+)(\s*->)', r'\1\2["\2"]\3', diagram_code)
    
    # Fix arrow syntax (ensure proper spacing)
    diagram_code = re.sub(r'(\w+|\])(\s*)-->', r'\1 --> ', diagram_code)
    diagram_code = re.sub(r'(\w+|\])(\s*)==>', r'\1 ==> ', diagram_code)
    diagram_code = re.sub(r'(\w+|\])(\s*)-.->', r'\1 -.-> ', diagram_code)
    
    # Fix class definitions (ensure proper syntax)
    diagram_code = re.sub(r'class(\s+)(\w+)(\s+)(\w+)', r'class \2 \4', diagram_code)
    
    return diagram_code

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
                                <!-- Improved diagram container with better rendering -->
                                <div class="diagram-container">
                                    <div class="svg-container" id="diagram-svg-{{ loop.index0 }}"></div>
                                    <pre class="mermaid" style="display: none;">{{ diagram_code }}</pre>
                                </div>
                                <!-- Error container that shows only when there's a rendering problem -->
                                <div class="error-container" id="error-container-{{ loop.index0 }}" style="display:none;">
                                    <div class="alert alert-warning">
                                        <h5>Diagram Rendering Issue</h5>
                                        <p>The diagram couldn't be rendered directly in this view.</p>
                                    </div>
                                </div>
                            </div>
                            <div class="card-footer">
                                <a href="/view_diagram/{{ loop.index0 }}" class="btn btn-primary" target="_blank">
                                    View in New Tab
                                </a>
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
                        // Hide notification
                        document.getElementById('diagramsNotification').style.display = 'none';
                        
                        // Re-render diagrams with our improved handling
                        renderDiagrams();
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
                    
                    // Re-render diagrams with new theme using our improved handler
                    setTimeout(() => {
                        renderDiagrams();
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
                    if (!question) return;
                    
                    // Disable submit button while processing
                    const submitButton = this.querySelector('button[type="submit"]');
                    submitButton.disabled = true;
                    
                    // Get the existing chat history from the page
                    const chatContainer = document.getElementById('chatMessages');
                    
                    // Check if the question already exists in the chat
                    const existingMessages = chatContainer.querySelectorAll('.user-message');
                    let isDuplicate = false;
                    
                    existingMessages.forEach(msg => {
                        const msgText = msg.textContent.replace('You:', '').trim();
                        if (msgText.toLowerCase() === question.toLowerCase()) {
                            isDuplicate = true;
                            // Highlight the existing message
                            msg.style.backgroundColor = '#ffffdd';
                            setTimeout(() => {
                                msg.style.backgroundColor = '';
                            }, 3000);
                        }
                    });
                    
                    if (isDuplicate) {
                        alert('This question has already been asked. Please check the existing answers or ask a different question.');
                        submitButton.disabled = false;
                        return;
                    }
                    
                    // Add the new message to the chat
                    const userMessage = document.createElement('div');
                    userMessage.className = 'user-message';
                    userMessage.innerHTML = '<strong>You:</strong> ' + question;
                    chatContainer.appendChild(userMessage);
                    
                    const botMessage = document.createElement('div');
                    botMessage.className = 'bot-message';
                    botMessage.innerHTML = '<strong>Bot:</strong> <span class="processing">Processing your question... <div class="spinner-border spinner-border-sm" role="status"></div></span>';
                    chatContainer.appendChild(botMessage);
                    
                    // Auto-scroll to bottom
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    
                    // Create form data
                    const formData = new FormData();
                    formData.append('question', question);
                    
                    // Send AJAX request
                    fetch('/ask', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Response:', data);
                        if (data.success) {
                            // Show a fake processing indicator
                            const processingSpan = document.querySelector('.processing');
                            if (processingSpan) {
                                // Simulate processing stages with timeouts
                                setTimeout(() => {
                                    processingSpan.innerHTML = "Finding information in documents... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                }, 2000);
                                
                                setTimeout(() => {
                                    processingSpan.innerHTML = "Creating vector embeddings... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                }, 4000);
                                
                                setTimeout(() => {
                                    processingSpan.innerHTML = "Generating answer... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                }, 7000);
                            }
                            
                            // Wait a bit longer (20 seconds) to ensure processing completes
                            setTimeout(() => {
                                window.location.reload();
                            }, 20000);
                        } else {
                            alert('Error: ' + (data.error || 'Unknown error'));
                            submitButton.disabled = false;
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error processing request: ' + error.message);
                        submitButton.disabled = false;
                    });
                    
                    // Clear the input
                    document.getElementById('question').value = '';
                });
            }
            
            // Session handling
            document.getElementById('createNewSession')?.addEventListener('click', function() {
                fetch('/new_session', {
                    method: 'POST'
                })
                .then(response => {
                    if (response.ok) {
                        window.location.reload();
                    }
                });
            });
            
            document.querySelectorAll('.switch-session').forEach(button => {
                button.addEventListener('click', function() {
                    const sessionId = this.getAttribute('data-session-id');
                    
                    const formData = new FormData();
                    formData.append('session_id', sessionId);
                    
                    fetch('/switch_session', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => {
                        if (response.ok) {
                            window.location.reload();
                        }
                    });
                });
            });
            
            // Advanced Mermaid diagram handling with better error recovery
            function renderDiagrams() {
                // Initialize with optimal configuration
                mermaid.initialize({ 
                    startOnLoad: false,
                    theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
                    securityLevel: 'loose',
                    logLevel: 'error',
                    fontFamily: 'arial, sans-serif',
                    flowchart: {
                        htmlLabels: true,
                        curve: 'basis',
                        padding: 15
                    }
                });
                
                // Find all diagram containers and render them individually
                document.querySelectorAll('.mermaid').forEach((diagram, index) => {
                    const diagramText = diagram.textContent.trim();
                    const targetDiv = document.getElementById(`diagram-svg-${index}`);
                    const errorContainer = document.getElementById(`error-container-${index}`);
                    
                    if (!targetDiv) return;
                    
                    try {
                        // Try to render using the newer Promise-based API
                        mermaid.render(`diagram-svg-content-${index}`, diagramText)
                            .then(result => {
                                targetDiv.innerHTML = result.svg;
                                if (errorContainer) errorContainer.style.display = 'none';
                            })
                            .catch(err => {
                                console.error(`Error rendering diagram ${index}:`, err);
                                handleRenderingError(diagramText, targetDiv, errorContainer, index);
                            });
                    } catch (err) {
                        console.error(`Initial mermaid error for diagram ${index}:`, err);
                        handleRenderingError(diagramText, targetDiv, errorContainer, index);
                    }
                });
                
                // Handler for diagram rendering errors
                function handleRenderingError(code, targetDiv, errorContainer, index) {
                    // Show error container
                    if (errorContainer) errorContainer.style.display = 'block';
                    
                    // Try alternative rendering as a last resort
                    try {
                        const fixedCode = fixFlowchartSyntax(code);
                        mermaid.render(`diagram-svg-fallback-${index}`, fixedCode)
                            .then(result => {
                                targetDiv.innerHTML = result.svg;
                            })
                            .catch(e => {
                                console.error(`Fallback rendering failed for diagram ${index}:`, e);
                                targetDiv.innerHTML = '<div class="alert alert-warning">Diagram rendering failed. Please use "View in New Tab" for a better viewing experience.</div>';
                            });
                    } catch (e) {
                        console.error(`Fallback mechanism failed for diagram ${index}:`, e);
                    }
                }
                
                // Extra syntax fixing function for flowcharts
                function fixFlowchartSyntax(code) {
                    // Try to detect and fix common syntax issues
                    let fixed = code;
                    
                    // Ensure proper flowchart declaration
                    if (!fixed.startsWith('flowchart')) {
                        fixed = 'flowchart TD\n' + fixed;
                    }
                    
                    // Add quotes to node text with spaces
                    fixed = fixed.replace(/\[([^\]]+)\]/g, function(match, p1) {
                        if (p1.includes(' ') && !p1.startsWith('"') && !p1.endsWith('"')) {
                            return '["' + p1 + '"]';
                        }
                        return match;
                    });
                    
                    // Fix arrow syntax
                    fixed = fixed.replace(/(\w+)--(\w+)/g, '$1 --> $2');
                    
                    return fixed;
                }
            }
            
            // Check if we have diagrams and show notification
            const hasDiagrams = document.querySelectorAll('.mermaid').length > 0;
            if (hasDiagrams) {
                // Show notification dot
                document.getElementById('diagramsNotification').style.display = 'block';
                
                // Try to render diagrams immediately
                renderDiagrams();
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
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11.6.0/dist/mermaid.min.js"></script>
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
            display: none;
        }
        .svg-container {
            width: 100%;
            overflow-x: auto;
            padding: 10px;
        }
        pre {
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <h1>{{ diagram_type|capitalize }} Diagram</h1>
    
    <div class="explanation">
        <h3>Explanation</h3>
        <p>{{ explanation }}</p>
    </div>
    
    <div class="diagram-container">
        <div class="svg-container" id="diagram-svg"></div>
        <pre class="mermaid" style="display: none;">{{ diagram_code }}</pre>
    </div>
    
    <div class="error-container" id="error-container">
        <h4>Diagram Rendering Error</h4>
        <p>There was an error rendering this diagram. Here's the raw diagram code:</p>
        <pre id="raw-code" class="border p-3 bg-light">{{ diagram_code }}</pre>
    </div>
    
    <a href="/" class="btn btn-primary">Back to Main App</a>
    
    <script>
        // Initialize mermaid with optimal configuration
        mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            logLevel: 'error',
            fontFamily: 'arial, sans-serif',
            fontSize: 16,
            flowchart: {
                htmlLabels: true,
                curve: 'basis',
                padding: 15
            }
        });
        
        // Render diagram with best practices
        document.addEventListener('DOMContentLoaded', function() {
            const diagramText = document.querySelector('.mermaid').textContent.trim();
            const targetDiv = document.getElementById('diagram-svg');
            
            try {
                mermaid.render('diagram-svg-content', diagramText)
                    .then(result => {
                        targetDiv.innerHTML = result.svg;
                    })
                    .catch(err => {
                        console.error('Mermaid rendering error:', err);
                        handleRenderingError();
                    });
            } catch (err) {
                console.error('Initial mermaid error:', err);
                handleRenderingError();
            }
            
            function handleRenderingError() {
                // Show error container with raw code
                document.getElementById('error-container').style.display = 'block';
                
                // Try alternative rendering as a last resort
                try {
                    const fixedCode = fixFlowchartSyntax(diagramText);
                    mermaid.render('diagram-svg-fallback', fixedCode)
                        .then(result => {
                            targetDiv.innerHTML = result.svg;
                            // Still show the raw code but indicate success
                            document.getElementById('error-container').classList.add('bg-success-subtle');
                            document.getElementById('error-container').querySelector('h4').textContent = 'Diagram Fixed';
                        })
                        .catch(e => {
                            console.error('Fallback rendering failed:', e);
                            targetDiv.innerHTML = '<div class="alert alert-warning">Unable to render diagram. Please check the raw code below.</div>';
                        });
                } catch (e) {
                    console.error('Fallback mechanism failed:', e);
                }
            }
            
            // Extra syntax fixing function for flowcharts
            function fixFlowchartSyntax(code) {
                // Try to detect and fix common syntax issues
                let fixed = code;
                
                // Ensure proper flowchart declaration
                if (!fixed.startsWith('flowchart')) {
                    fixed = 'flowchart TD\n' + fixed;
                }
                
                // Add quotes to node text with spaces
                fixed = fixed.replace(/\[([^\]]+)\]/g, function(match, p1) {
                    if (p1.includes(' ') && !p1.startsWith('"') && !p1.endsWith('"')) {
                        return '["' + p1 + '"]';
                    }
                    return match;
                });
                
                // Fix arrow syntax
                fixed = fixed.replace(/(\w+)--(\w+)/g, '$1 --> $2');
                
                return fixed;
            }
        });
    </script>
</body>
</html>
    """, diagram_code=diagram_code, explanation=explanation, diagram_type=diagram_type)

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