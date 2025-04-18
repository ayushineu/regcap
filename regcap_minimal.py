"""
RegCap GPT - Minimal Working Version

This is a streamlined version of the RegCap GPT application with minimal
but essential functionality. This version focuses on ensuring the core
features work correctly.
"""

from flask import Flask, render_template_string, session, request, jsonify
import os
import uuid
import threading
import time
import json
import base64
import io
import PyPDF2
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "regcap-minimal-secret-key"

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Simple in-memory storage
session_store = {}
document_store = {}
chat_history_store = {}
question_status_store = {}
question_session_map = {}
vector_store = {}

def get_current_session():
    """Get or create the current session ID."""
    if 'current_session' not in session:
        session['current_session'] = str(uuid.uuid4())
    return session['current_session']

def create_new_session():
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    session['current_session'] = session_id
    return session_id

def get_document_chunks():
    """Get document chunks for the current session."""
    session_id = get_current_session()
    return document_store.get(session_id, [])

def get_chat_history():
    """Get chat history for the current session."""
    session_id = get_current_session()
    return chat_history_store.get(session_id, [])

def list_all_sessions():
    """List all available sessions."""
    return list(session_store.keys())

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def chunk_text(text, chunk_size=1000, overlap=100):
    """Split text into overlapping chunks of approximately equal size."""
    if not text:
        return []
        
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Try to end at a period or newline for more natural chunks
        if end < text_len:
            # Look for a good breaking point
            breakpoint = text.rfind('.', start, end)
            if breakpoint == -1:
                breakpoint = text.rfind('\n', start, end)
            
            if breakpoint != -1 and breakpoint > start + chunk_size // 2:
                end = breakpoint + 1
        
        # Create the chunk and add to list
        chunks.append(text[start:end])
        
        # Move the start position for the next chunk, with overlap
        start = end - overlap
    
    return chunks

def generate_answer_with_openai(question, context):
    """Generate an answer using OpenAI API"""
    try:
        prompt = f"""You are RegCap GPT, a regulatory intelligence assistant. 
        
Answer the following question based ONLY on the provided context:
        
CONTEXT:
{context}

QUESTION:
{question}

Your answer should be detailed, accurate, and focused only on the regulatory information in the context.
If the answer cannot be found in the context, reply with "I don't have enough information to answer that question."
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are a helpful regulatory intelligence assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return f"I'm sorry, but I encountered an error when trying to generate a response: {str(e)}"

def generate_diagram_with_openai(question, context):
    """Generate a Mermaid diagram using OpenAI API"""
    try:
        prompt = f"""You are RegCap GPT, a regulatory intelligence assistant that specializes in creating visualizations.

Based on the following context and question, generate a Mermaid diagram that visualizes the relevant process, flow, or structure.

CONTEXT:
{context}

QUESTION:
{question}

Generate ONLY the Mermaid diagram code without any other explanation. 
The diagram should be a flowchart (using flowchart TD syntax) unless the question specifically asks for another type.
Make sure the diagram is clear, focused, and properly formatted with Mermaid syntax.
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are a helpful regulatory intelligence assistant that specializes in creating visualizations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        diagram_code = response.choices[0].message.content.strip()
        
        # Generate an explanation for the diagram
        explanation_prompt = f"""Provide a brief explanation of the diagram that you just created in response to:
        
QUESTION:
{question}

Explain what the diagram shows and how it addresses the question.
"""
        
        explanation_response = openai_client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are a helpful regulatory intelligence assistant."},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": diagram_code},
                {"role": "user", "content": explanation_prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        explanation = explanation_response.choices[0].message.content.strip()
        
        return diagram_code, explanation
    except Exception as e:
        print(f"OpenAI diagram generation error: {e}")
        return None, f"Error generating diagram: {str(e)}"

def detect_diagram_request(question):
    """Detect if the question is asking for a diagram or visualization"""
    diagram_keywords = [
        "diagram", "flow", "flowchart", "process", "map", "visual", "visualize", 
        "structure", "sequence", "workflow", "draw", "chart", "graph", "illustration"
    ]
    
    question_lower = question.lower()
    for keyword in diagram_keywords:
        if keyword in question_lower:
            return True
    
    # Check for specific diagram requests
    if "show me" in question_lower and any(term in question_lower for term in ["how", "process", "flow", "structure"]):
        return True
        
    return False

def update_question_status(question_id, stage=None, progress=None, done=None, error=None, answer=None, has_diagram=None, diagram_code=None):
    """Update the status of a question being processed in the background."""
    if question_id not in question_status_store:
        question_status_store[question_id] = {}
    
    if stage is not None:
        question_status_store[question_id]['stage'] = stage
    
    if progress is not None:
        question_status_store[question_id]['progress'] = progress
    
    if done is not None:
        question_status_store[question_id]['done'] = done
    
    if error is not None:
        question_status_store[question_id]['error'] = error
        
    if answer is not None:
        question_status_store[question_id]['answer'] = answer
        
    if has_diagram is not None:
        question_status_store[question_id]['has_diagram'] = has_diagram
        
    if diagram_code is not None:
        question_status_store[question_id]['diagram_code'] = diagram_code

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
    <style>
        :root {
            --primary-color: #0088cc;
            --primary-hover: #0073ad;
            --secondary-color: #64748b;
            --primary-bg: #ffffff;
            --secondary-bg: #f8fafc;
            --tertiary-bg: #f1f5f9;
            --primary-text: #0f172a;
            --secondary-text: #475569;
            --light-text: #ffffff;
            --border-color: #e2e8f0;
            --sidebar-bg: #f1f5f9;
            --sidebar-active: #e0f2ff;
            --border-radius: 8px;
        }
        
        [data-theme="dark"] {
            --primary-color: #0088cc;
            --primary-hover: #1a9fe0;
            --secondary-color: #94a3b8;
            --primary-bg: #111827;
            --secondary-bg: #1e293b;
            --tertiary-bg: #334155;
            --primary-text: #f1f5f9;
            --secondary-text: #cbd5e1;
            --light-text: #ffffff;
            --border-color: #475569;
            --sidebar-bg: #1e293b;
            --sidebar-active: #2d3748;
        }
        
        body {
            background-color: var(--primary-bg);
            color: var(--primary-text);
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 0;
            height: 100vh;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .app-container {
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        
        .sidebar {
            width: 260px;
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
            overflow-y: auto;
            flex-shrink: 0;
        }
        
        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .sidebar-header h1 {
            font-size: 1.5rem;
            margin: 0;
            color: var(--primary-color);
        }
        
        .sidebar-nav {
            padding: 1rem 0;
            flex-grow: 1;
        }
        
        .nav-item {
            padding: 0.75rem 1.5rem;
            margin: 0.25rem 0.75rem;
            border-radius: var(--border-radius);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--secondary-text);
        }
        
        .nav-item:hover {
            background-color: var(--sidebar-active);
            color: var(--primary-text);
        }
        
        .nav-item.active {
            background-color: var(--sidebar-active);
            color: var(--primary-color);
            font-weight: 500;
        }
        
        .main-content {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }
        
        .header h2 {
            margin: 0;
            font-weight: 600;
            font-size: 1.25rem;
        }
        
        .content-area {
            padding: 2rem;
            flex-grow: 1;
            overflow-y: auto;
        }
        
        .content-panel {
            display: none;
        }
        
        .content-panel.active {
            display: block;
        }
        
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
        }
        
        .user-message {
            background-color: var(--primary-color);
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
        
        .theme-toggle {
            background-color: var(--secondary-bg);
            color: var(--secondary-text);
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
        }
        
        .theme-toggle:hover {
            background-color: var(--tertiary-bg);
        }
        
        .beta-banner {
            background-color: #fff3cd;
            color: #856404;
            padding: 0.4rem 1rem;
            text-align: center;
            font-size: 0.8rem;
            position: relative;
            z-index: 1000;
        }
        
        [data-theme="dark"] .beta-banner {
            background-color: #2d3748;
            color: #fbd38d;
        }
    </style>
</head>
<body>
    <div class="beta-banner">
        🚧 Beta Notice: RegCap GPT is currently in active development. Some features may be limited or evolving. Thank you for testing and sharing feedback!
    </div>
    <div class="app-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1><i class="fa fa-book"></i> RegCap GPT</h1>
                <div>Regulatory Intelligence</div>
            </div>
            
            <div class="sidebar-nav">
                <div class="nav-item active" data-panel="chat-panel">
                    <i class="fa fa-comments"></i> Chat
                </div>
                <div class="nav-item" data-panel="docs-panel">
                    <i class="fa fa-file-pdf-o"></i> Documents
                </div>
                <div class="nav-item" data-panel="sessions-panel">
                    <i class="fa fa-database"></i> Sessions
                </div>
                
                <div class="nav-item" id="featureToggle">
                    <i class="fa fa-list"></i> Features <i class="fa fa-angle-down toggle-icon"></i>
                </div>
                <div id="featureList" style="display: none; padding-left: 2rem;">
                    <div class="small text-muted py-1"><i class="fa fa-check text-success"></i> PDF Document Analysis</div>
                    <div class="small text-muted py-1"><i class="fa fa-check text-success"></i> AI-powered Q&A</div>
                    <div class="small text-muted py-1"><i class="fa fa-check text-success"></i> Diagram Generation</div>
                    <div class="small text-muted py-1"><i class="fa fa-check text-success"></i> Session Management</div>
                    <div class="small text-muted py-1"><i class="fa fa-check text-success"></i> Dark/Light Theme</div>
                </div>
            </div>
        </div>
        
        <!-- Main Content Area -->
        <div class="main-content">
            <!-- Header -->
            <div class="header">
                <h2 id="currentPanelTitle"><i class="fa fa-comments"></i> Chat with your Documents</h2>
                <button id="themeToggle" class="theme-toggle">
                    <i class="fa fa-moon-o"></i> Dark Mode
                </button>
            </div>
            
            <!-- Content Area -->
            <div class="content-area">
                <!-- Chat Panel -->
                <div id="chat-panel" class="content-panel active">
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
                </div>
                
                <!-- Documents Panel -->
                <div id="docs-panel" class="content-panel">
                    <div class="card mb-4">
                        <div class="card-header">Upload Documents</div>
                        <div class="card-body">
                            <form id="uploadForm" enctype="multipart/form-data">
                                <div class="mb-3">
                                    <label for="documentUpload" class="form-label">Select PDF documents to upload</label>
                                    <input class="form-control" type="file" id="documentUpload" name="files" multiple accept=".pdf">
                                </div>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fa fa-upload"></i> Upload Files
                                </button>
                            </form>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">Uploaded Documents</div>
                        <div class="card-body">
                            {% if documents %}
                                <div class="list-group">
                                    {% for doc in documents %}
                                        <div class="list-group-item">
                                            <i class="fa fa-file-pdf-o text-danger me-2"></i> {{ doc.name }}
                                        </div>
                                    {% endfor %}
                                </div>
                            {% else %}
                                <p class="text-muted mb-0">No documents uploaded yet.</p>
                            {% endif %}
                        </div>
                    </div>
                </div>
                
                <!-- Sessions Panel -->
                <div id="sessions-panel" class="content-panel">
                    <div class="card mb-4">
                        <div class="card-header">Current Session</div>
                        <div class="card-body">
                            <p class="mb-3">You are currently in session: <strong>{{ session_id }}</strong></p>
                            <button id="newSessionBtn" class="btn btn-primary">
                                <i class="fa fa-plus-circle"></i> Create New Session
                            </button>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">Available Sessions</div>
                        <div class="card-body">
                            {% if sessions %}
                                <div class="list-group">
                                    {% for s_id in sessions %}
                                        <button class="list-group-item list-group-item-action session-switch-btn" 
                                            data-session-id="{{ s_id }}">
                                            Switch to Session {{ s_id }}
                                        </button>
                                    {% endfor %}
                                </div>
                            {% else %}
                                <p class="text-muted mb-0">No other sessions available.</p>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            // Feature toggle functionality
            var featureToggle = document.getElementById('featureToggle');
            var featureList = document.getElementById('featureList');
            
            if (featureToggle && featureList) {
                featureToggle.addEventListener('click', function() {
                    var toggleIcon = this.querySelector('.toggle-icon');
                    
                    if (featureList.style.display === 'none') {
                        featureList.style.display = 'block';
                        if (toggleIcon) {
                            toggleIcon.className = 'fa fa-angle-up toggle-icon';
                        }
                    } else {
                        featureList.style.display = 'none';
                        if (toggleIcon) {
                            toggleIcon.className = 'fa fa-angle-down toggle-icon';
                        }
                    }
                });
            }
            
            // Tab navigation
            const navItems = document.querySelectorAll('.nav-item');
            const contentPanels = document.querySelectorAll('.content-panel');
            const currentPanelTitle = document.getElementById('currentPanelTitle');
            
            const panelTitles = {
                'chat-panel': '<i class="fa fa-comments"></i> Chat with your Documents',
                'docs-panel': '<i class="fa fa-file-pdf-o"></i> Document Management',
                'sessions-panel': '<i class="fa fa-database"></i> Session Management'
            };
            
            navItems.forEach(item => {
                item.addEventListener('click', function() {
                    // Skip if this is the feature toggle
                    if (this.id === 'featureToggle') {
                        return;
                    }
                    
                    const panelId = this.getAttribute('data-panel');
                    if (!panelId) return;
                    
                    // Hide all panels
                    contentPanels.forEach(panel => {
                        panel.classList.remove('active');
                    });
                    
                    // Remove active class from all nav items
                    navItems.forEach(navItem => {
                        navItem.classList.remove('active');
                    });
                    
                    // Show selected panel
                    const selectedPanel = document.getElementById(panelId);
                    if (selectedPanel) {
                        selectedPanel.classList.add('active');
                    }
                    
                    // Update panel title
                    if (panelTitles[panelId]) {
                        currentPanelTitle.innerHTML = panelTitles[panelId];
                    }
                    
                    // Add active class to clicked nav item
                    this.classList.add('active');
                });
            });
            
            // Theme toggle
            const themeToggle = document.getElementById('themeToggle');
            const savedTheme = localStorage.getItem('theme');
            
            // Apply saved theme
            if (savedTheme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                themeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
            }
            
            themeToggle.addEventListener('click', function() {
                if (document.documentElement.getAttribute('data-theme') === 'dark') {
                    document.documentElement.removeAttribute('data-theme');
                    localStorage.setItem('theme', 'light');
                    this.innerHTML = '<i class="fa fa-moon-o"></i> Dark Mode';
                } else {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                    this.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                }
            });
            
            // Question form
            const questionForm = document.getElementById('questionForm');
            const questionInput = document.getElementById('questionInput');
            const chatMessages = document.getElementById('chatMessages');
            
            // Document upload form
            const uploadForm = document.getElementById('uploadForm');
            
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const fileInput = document.getElementById('documentUpload');
                    const files = fileInput.files;
                    
                    if (!files || files.length === 0) {
                        alert('Please select at least one file to upload');
                        return;
                    }
                    
                    const formData = new FormData();
                    for (let i = 0; i < files.length; i++) {
                        formData.append('files', files[i]);
                    }
                    
                    // Show loading indicator
                    const uploadButton = uploadForm.querySelector('button[type="submit"]');
                    const originalButtonText = uploadButton.innerHTML;
                    uploadButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Uploading...';
                    uploadButton.disabled = true;
                    
                    fetch('/upload-files', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        uploadButton.innerHTML = originalButtonText;
                        uploadButton.disabled = false;
                        
                        if (data.success) {
                            alert('Files uploaded successfully');
                            // Refresh the page to show the newly uploaded documents
                            location.reload();
                        } else {
                            console.error('Error uploading files:', data);
                            alert('Error uploading files: ' + (data.error || 'Unknown error'));
                        }
                    })
                    .catch(error => {
                        console.error('Error uploading files:', error);
                        uploadButton.innerHTML = originalButtonText;
                        uploadButton.disabled = false;
                        alert('Error uploading files: ' + error.message);
                    });
                });
            }
            
            // Question form
            if (questionForm) {
                questionForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const question = questionInput.value.trim();
                    if (!question) return;
                    
                    // Add user message to chat
                    if (chatMessages.querySelector('.text-center.text-muted')) {
                        chatMessages.innerHTML = ''; // Clear the "No chat history" message
                    }
                    
                    const userDiv = document.createElement('div');
                    userDiv.className = 'user-message';
                    userDiv.innerHTML = '<strong>You:</strong> ' + question;
                    chatMessages.appendChild(userDiv);
                    
                    // Add processing message
                    const processingDiv = document.createElement('div');
                    processingDiv.className = 'bot-message';
                    processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <i class="fa fa-spinner fa-spin"></i> Processing your question...';
                    chatMessages.appendChild(processingDiv);
                    
                    // Clear input and scroll to bottom
                    questionInput.value = '';
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Send question to server
                    fetch('/ask-question', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            question: question
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const questionId = data.question_id;
                            
                            // Poll for status
                            const pollInterval = setInterval(function() {
                                fetch('/question-status/' + questionId)
                                    .then(response => response.json())
                                    .then(status => {
                                        if (status.done) {
                                            clearInterval(pollInterval);
                                            
                                            if (status.error) {
                                                processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error: ' + status.error + '</span>';
                                            } else {
                                                processingDiv.innerHTML = '<strong>RegCap GPT:</strong> ' + status.answer;
                                                
                                                // Handle diagram if present
                                                if (status.has_diagram && status.diagram_code) {
                                                    const diagramDiv = document.createElement('div');
                                                    diagramDiv.className = 'bot-message';
                                                    diagramDiv.innerHTML = '<strong>Diagram:</strong><pre style="background-color:#f8f9fa; padding:10px; border-radius:5px; margin-top:10px;">' + 
                                                        status.diagram_code + '</pre>';
                                                    chatMessages.appendChild(diagramDiv);
                                                }
                                            }
                                            
                                            chatMessages.scrollTop = chatMessages.scrollHeight;
                                        } else if (status.stage && status.progress) {
                                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <i class="fa fa-spinner fa-spin"></i> ' + 
                                                status.stage + ' (' + status.progress + '%)';
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error checking status:', error);
                                        clearInterval(pollInterval);
                                        processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error checking question status</span>';
                                    });
                            }, 1000);
                        } else {
                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error: ' + 
                                (data.error || 'Failed to process question') + '</span>';
                        }
                    })
                    .catch(error => {
                        console.error('Error submitting question:', error);
                        processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error submitting question</span>';
                    });
                });
            }
            
            // Document upload
            const uploadForm = document.getElementById('uploadForm');
            
            if (uploadForm) {
                uploadForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const fileInput = document.getElementById('documentUpload');
                    if (fileInput.files.length === 0) {
                        alert('Please select at least one file to upload.');
                        return;
                    }
                    
                    const formData = new FormData();
                    for (let i = 0; i < fileInput.files.length; i++) {
                        formData.append('files', fileInput.files[i]);
                    }
                    
                    const submitBtn = this.querySelector('button[type="submit"]');
                    const originalBtnText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Uploading...';
                    submitBtn.disabled = true;
                    
                    fetch('/upload-files', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Files uploaded successfully!');
                            window.location.reload();
                        } else {
                            alert('Error: ' + (data.error || 'Failed to upload files'));
                            submitBtn.innerHTML = originalBtnText;
                            submitBtn.disabled = false;
                        }
                    })
                    .catch(error => {
                        console.error('Error uploading files:', error);
                        alert('Error uploading files');
                        submitBtn.innerHTML = originalBtnText;
                        submitBtn.disabled = false;
                    });
                });
            }
            
            // New session
            const newSessionBtn = document.getElementById('newSessionBtn');
            
            if (newSessionBtn) {
                newSessionBtn.addEventListener('click', function() {
                    if (confirm('Create a new session? This will start with a clean slate.')) {
                        fetch('/new-session', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({}) // Add an empty body to avoid potential issues
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert('New session created successfully!');
                                window.location.reload();
                            } else {
                                console.error('Error details:', data);
                                alert('Error: ' + (data.error || 'Failed to create new session'));
                            }
                        })
                        .catch(error => {
                            console.error('Error creating new session:', error);
                            alert('Error creating new session');
                        });
                    }
                });
            }
            
            // Session switch
            const sessionSwitchBtns = document.querySelectorAll('.session-switch-btn');
            
            sessionSwitchBtns.forEach(btn => {
                btn.addEventListener('click', function() {
                    const sessionId = this.getAttribute('data-session-id');
                    
                    if (confirm('Switch to session ' + sessionId + '?')) {
                        fetch('/switch-session', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                session_id: sessionId
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert('Switched to session ' + sessionId);
                                window.location.reload();
                            } else {
                                alert('Error: ' + (data.error || 'Failed to switch session'));
                            }
                        })
                        .catch(error => {
                            console.error('Error switching session:', error);
                            alert('Error switching session');
                        });
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

@app.route('/new-session', methods=['POST'])
def new_session():
    """Create a new session."""
    try:
        session_id = create_new_session()
        session_store[session_id] = {'created_at': time.time()}
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/switch-session', methods=['POST'])
def switch_session():
    """Switch to a different session."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'})
            
        # Store the session ID in the Flask session
        session['current_session'] = session_id
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload-files', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No files were uploaded'})
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'No selected files'})
    
    # Process uploaded files
    session_id = get_current_session()
    if session_id not in document_store:
        document_store[session_id] = []
    
    for file in files:
        if file and file.filename.endswith('.pdf'):
            try:
                # Extract text from PDF
                pdf_text = extract_text_from_pdf(file)
                
                # Split text into manageable chunks
                text_chunks = chunk_text(pdf_text)
                
                # Store the file information and chunked content
                document_store[session_id].append({
                    'name': file.filename,
                    'chunks': text_chunks,
                    'date_uploaded': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                
                print(f"Processed {file.filename}: {len(text_chunks)} chunks created")
            except Exception as e:
                print(f"Error processing {file.filename}: {e}")
                return jsonify({'success': False, 'error': f'Error processing {file.filename}: {str(e)}'})
    
    return jsonify({'success': True, 'message': f'Processed {len(files)} files'})

@app.route('/ask-question', methods=['POST'])
def ask_question():
    """Handle questions from the user."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})
        
        # Generate a question ID
        question_id = str(uuid.uuid4())
        
        # Store the current session ID with the question ID
        current_session_id = get_current_session()
        
        # Store the session ID for this question in global map
        question_session_map[question_id] = current_session_id
        
        # Initialize status
        update_question_status(
            question_id,
            stage="Processing",
            progress=0,
            done=False
        )
        
        # Start processing in a background thread
        threading.Thread(target=process_question, args=(question, question_id)).start()
        
        return jsonify({'success': True, 'question_id': question_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def process_question(question, question_id):
    """Process a question in the background."""
    try:
        # Get the session ID from the global question_session_map
        session_id = question_session_map.get(question_id)
        if not session_id:
            # Fallback to the first session in the store if we can't find the mapping
            session_id = list(session_store.keys())[0] if session_store else str(uuid.uuid4())
        
        # Get available documents for this session
        documents = document_store.get(session_id, [])
        
        # Update status
        update_question_status(question_id, stage="Analyzing question", progress=20, done=False)
        
        # Check if this is a diagram request
        is_diagram_request = detect_diagram_request(question)
        
        # Update status
        update_question_status(
            question_id, 
            stage="Searching for relevant information", 
            progress=40, 
            done=False
        )
        
        # Collect context from document chunks
        context = ""
        if documents:
            for doc in documents:
                if 'chunks' in doc and doc['chunks']:
                    # For simplicity, we're using all chunks from all documents
                    # In a more advanced version, we would use vector search to find relevant chunks
                    for chunk in doc['chunks'][:3]:  # Limit to 3 chunks per document to avoid context window issues
                        context += chunk + "\n\n"
        
        # If no documents are available, provide a message
        if not context:
            context = "No document content available. Please upload some PDF documents first."
        
        # Update status
        update_question_status(question_id, stage="Generating response", progress=75, done=False)
        
        # Set default values
        answer = ""
        has_diagram = False
        diagram_code = None
        
        # Process based on diagram request or regular question
        if is_diagram_request and context != "No document content available. Please upload some PDF documents first.":
            # Generate diagram and explanation
            diagram_code, explanation = generate_diagram_with_openai(question, context)
            answer = explanation
            has_diagram = True if diagram_code else False
        else:
            # Generate regular answer
            answer = generate_answer_with_openai(question, context)
        
        # If context is empty, give a helpful response
        if context == "No document content available. Please upload some PDF documents first.":
            answer = "I don't have any documents to analyze yet. Please upload some PDF documents using the Documents tab, and then I can answer your questions based on their content."
        
        # Update status as complete
        update_question_status(
            question_id,
            stage="Complete",
            progress=100,
            done=True,
            answer=answer,
            has_diagram=has_diagram,
            diagram_code=diagram_code
        )
        
        # Save to chat history
        if session_id not in chat_history_store:
            chat_history_store[session_id] = []
        
        chat_history_store[session_id].append((question, answer))
        
    except Exception as e:
        # Log the error
        print(f"Error processing question: {str(e)}")
        
        # Update status with error
        update_question_status(
            question_id,
            stage="Error",
            progress=100,
            done=True,
            error=f"Error processing question: {str(e)}"
        )

@app.route('/question-status/<question_id>', methods=['GET'])
def get_question_status(question_id):
    """Get the status of a specific question."""
    if question_id in question_status_store:
        return jsonify(question_status_store[question_id])
    return jsonify({'error': 'Question ID not found'})

if __name__ == '__main__':
    # Create a default session
    default_session_id = str(uuid.uuid4())
    session_store[default_session_id] = {'created_at': time.time()}
    
    app.run(host='0.0.0.0', port=5004)