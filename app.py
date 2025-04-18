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
# Import the fix_mermaid_syntax function with better error handling
try:
    from fix_mermaid import fix_mermaid_syntax
    print("Successfully imported fix_mermaid module")
except Exception as e:
    print(f"Error importing fix_mermaid: {str(e)}")
    # Define a fallback version if import fails
    def fix_mermaid_syntax(diagram_code, diagram_type="flowchart"):
        """Basic fallback if the full module is not available"""
        import re
        
        if not diagram_code:
            return "graph TD\nA(Empty Diagram)"
        
        # Basic fixes for compatibility
        if diagram_type == "flowchart":
            diagram_code = diagram_code.replace("flowchart TD", "graph TD")
            diagram_code = diagram_code.replace("flowchart LR", "graph LR")
            diagram_code = re.sub(r'([A-Za-z0-9_-]+)\[([^\]]+)\]', r'\1(\2)', diagram_code)
            
        # Remove potentially problematic styling
        diagram_code = re.sub(r'style\s+\w+\s+.*?\n', '\n', diagram_code)
        diagram_code = re.sub(r'classDef.*?\n', '\n', diagram_code)
        diagram_code = re.sub(r'class\s+.*?\n', '\n', diagram_code)
        
        return diagram_code

try:
    from flask_app import (
        # Data storage and session management
        SimpleStorage, get_current_session, create_new_session, 
        encode_for_storage, decode_from_storage, 
        
        # Document processing
        extract_text_from_pdf, save_document_chunks, get_document_chunks, get_all_document_chunks,
        
        # Vector search and embedding
        get_embedding, create_vector_store, get_similar_chunks,
        
        # History and storage management
        save_chat_history, get_chat_history, save_diagram, get_diagrams,
        list_all_sessions, log_message
    )
    
    # Import OpenAI helper functions
    from utils.openai_helper import generate_answer, generate_diagram, detect_diagram_request
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
        
    # Fallbacks for OpenAI helper functions
    def generate_answer(question, context_chunks):
        return "I'm unable to generate an answer because the OpenAI API is not available."
        
    def generate_diagram(question, context_chunks, diagram_type="flowchart"):
        return False, "Unable to generate a diagram because the OpenAI API is not available."
        
    def detect_diagram_request(question):
        return False, None

# Create our question status tracking system
question_status_store = {}

def update_question_status(question_id, stage=None, progress=None, done=None, error=None, answer=None, has_diagram=None, diagram_code=None):
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
            "error": None,
            "answer": None,
            "has_diagram": False,
            "diagram_code": None
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
        
    if answer:
        current_status["answer"] = answer
        
    if has_diagram is not None:
        current_status["has_diagram"] = has_diagram
        
    if diagram_code:
        current_status["diagram_code"] = diagram_code

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
    <script src="https://cdn.jsdelivr.net/npm/mermaid@8.14.0/dist/mermaid.min.js"></script>
    <script>
        // Initialize mermaid with specific configuration for better compatibility
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            logLevel: 'error',
            securityLevel: 'loose',
            flowchart: { 
                useMaxWidth: true, 
                htmlLabels: true,
                curve: 'basis'
            },
            themeVariables: {
                primaryColor: '#0088cc',
                primaryTextColor: '#ffffff',
                primaryBorderColor: '#7C0000',
                lineColor: '#0088cc',
                secondaryColor: '#006699',
                tertiaryColor: '#f1f5f9'
            }
        });
    </script>
    <style>
        /* Core styles */
        :root {
            --primary-color: #0088cc; /* Darker Barclays blue */
            --primary-hover: #0073ad;
            --secondary-color: #64748b;
            --accent-color: #00a3d9;
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
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.08);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.05);
        }
        
        [data-theme="dark"] {
            --primary-color: #0088cc; /* Darker Barclays blue */
            --primary-hover: #1a9fe0;
            --secondary-color: #94a3b8;
            --accent-color: #33addb;
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
            transition: all 0.3s ease;
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.5;
            margin: 0;
            padding: 0;
            height: 100vh;
            overflow: hidden;
        }
        
        /* Main layout structure */
        .app-container {
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        
        /* Sidebar styles */
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
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }
        
        .sidebar-header h1 {
            font-size: 1.25rem;
            margin: 0 0 0.25rem 0;
            font-weight: 700;
            color: var(--primary-color);
        }
        
        .sidebar-header .byline {
            font-size: 0.85rem;
            color: var(--secondary-text);
            font-style: italic;
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
            transition: all 0.2s ease;
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
        
        .sidebar-footer {
            padding: 1rem 1.5rem;
            border-top: 1px solid var(--border-color);
        }
        
        /* Main content area */
        .main-content {
            flex-grow: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        /* Beta banner */
        .beta-banner {
            background-color: #d9ecf7;
            border-bottom: 1px solid #a6d5ea;
            padding: 0.75rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        [data-theme="dark"] .beta-banner {
            background-color: #00689b;
            border-color: #0073ad;
        }
        
        .beta-banner-content {
            color: #00689b;
            font-size: 0.85rem;
            line-height: 1.3;
        }
        
        [data-theme="dark"] .beta-banner-content {
            color: #a6d5ea;
        }
        
        .beta-close-btn {
            background: none;
            border: none;
            color: #00689b;
            cursor: pointer;
            font-size: 1.2rem;
            padding: 0;
            margin-left: 0.5rem;
        }
        
        .beta-close-btn:hover {
            color: #0088cc;
        }
        
        /* Header */
        .header {
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            background-color: var(--primary-bg);
        }
        
        .header h2 {
            margin: 0;
            font-weight: 600;
            font-size: 1.25rem;
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
        
        /* Content area */
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
        
        /* Content styles */
        .chat-container {
            height: calc(100vh - 320px);
            min-height: 300px;
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
        
        /* Diagram specific styles */
        .mermaid-container {
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            overflow: auto;
            max-width: 100%;
        }
        
        /* Dark theme support for diagrams */
        [data-theme="dark"] .mermaid-container {
            background-color: #1e293b;
        }
        
        /* Style for diagram messages */
        .diagram-message {
            max-width: 95% !important; /* Allow diagrams to be wider */
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
            .app-container {
                flex-direction: column;
                height: auto;
            }
            
            .sidebar {
                width: 100%;
                height: auto;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
            }
            
            .sidebar-nav {
                display: flex;
                flex-wrap: wrap;
                padding: 0.5rem;
            }
            
            .nav-item {
                margin: 0.25rem;
                padding: 0.5rem 1rem;
                flex-grow: 1;
                text-align: center;
            }
            
            .sidebar-footer {
                display: none; /* Hide sidebar footer on mobile */
            }
            
            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 0.5rem;
                padding: 1rem;
            }
            
            .header > div {
                width: 100%;
                justify-content: flex-end;
            }
            
            .content-area {
                padding: 1rem;
            }
            
            .chat-container {
                height: 400px; /* Fixed height on mobile */
            }
            
            /* Add theme toggle to header for mobile */
            .header .theme-toggle-mobile {
                display: block;
                margin-top: 0.5rem;
            }
        }
        
        /* Hide mobile theme toggle by default */
        /* Display the mobile theme toggle at all times */
        .theme-toggle-mobile {
            display: block;
            margin-left: auto; /* Push to the right */
        }
        
        /* Feature list styles */
        /* We don't need special styling for the features item, 
           it should use the same styles as other nav-items */
        
        .feature-list {
            background-color: var(--tertiary-bg);
            margin: 0 0.75rem;
            padding: 1rem;
            border-radius: var(--border-radius);
            font-size: 0.9rem;
        }
        
        .feature-list-date {
            font-size: 0.8rem;
            color: var(--secondary-text);
            margin-bottom: 0.75rem;
            text-align: right;
            font-style: italic;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        .feature-list ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .feature-list li {
            padding: 0.4rem 0;
            font-size: 0.9rem;
            display: flex;
            align-items: flex-start;
        }
        
        .feature-list li i {
            color: var(--primary-color);
            margin-right: 0.5rem;
            min-width: 16px;
            margin-top: 0.2rem;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1><i class="fa fa-book"></i> RegCap GPT</h1>
                <div class="byline">Regulatory Intelligence</div>
            </div>
            
            <div class="sidebar-nav">
                <div class="nav-item active" data-panel="chat-panel">
                    <i class="fa fa-comments"></i> Chat
                </div>
                <div class="nav-item" data-panel="docs-panel">
                    <i class="fa fa-file-pdf-o"></i> Documents
                </div>
                <div class="nav-item" data-panel="diagrams-panel">
                    <i class="fa fa-sitemap"></i> Diagrams
                </div>
                <div class="nav-item" data-panel="sessions-panel">
                    <i class="fa fa-database"></i> Sessions
                </div>
                <div class="nav-item" id="featureToggle">
                    <i class="fa fa-list"></i> Features <span class="float-end"><i class="fa fa-angle-down toggle-icon"></i></span>
                </div>
                <div class="feature-list" id="featureList" style="display: none;">
                    <div class="feature-list-date">As of April 18, 2025</div>
                    <ul>
                        <li><i class="fa fa-check"></i> PDF document analysis</li>
                        <li><i class="fa fa-check"></i> Natural language queries</li>
                        <li><i class="fa fa-check"></i> AI-generated diagrams</li>
                        <li><i class="fa fa-check"></i> Multi-session support</li>
                        <li><i class="fa fa-check"></i> Vector search technology</li>
                        <li><i class="fa fa-check"></i> Dark/light mode</li>
                    </ul>
                </div>
            </div>
            
            <div class="sidebar-footer">
                <div class="text-center" style="font-size: 0.85rem;">
                    <i class="fa fa-info-circle"></i> 
                    Session: <strong>{{ session_id }}</strong>
                </div>
            </div>
        </div>
        
        <!-- Main Content Area -->
        <div class="main-content">
            <!-- Beta Banner -->
            <div id="betaBanner" class="beta-banner">
                <div class="beta-banner-content">
                    🚧 Beta Notice: RegCap GPT is currently in active development. Some features may be limited or evolving. Thank you for testing and sharing feedback!
                </div>
                <button class="beta-close-btn" onclick="document.getElementById('betaBanner').style.display='none';">&times;</button>
            </div>
            
            <!-- Header -->
            <div class="header">
                <h2 id="currentPanelTitle"><i class="fa fa-comments"></i> Chat with your Documents</h2>
                <div class="d-flex align-items-center gap-3 justify-content-end">
                    <button id="mobileThemeToggle" class="theme-toggle theme-toggle-mobile">
                        <i class="fa fa-moon-o"></i> Dark Mode
                    </button>
                </div>
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
                    
                    <div class="alert alert-info" role="alert">
                        <i class="fa fa-lightbulb-o"></i> <strong>Tip:</strong> 
                        You can ask for diagrams by using phrases like "create a flowchart", 
                        "draw a diagram", or "visualize the process".
                    </div>
                </div>
                
                <!-- Documents Panel -->
                <div id="docs-panel" class="content-panel">
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
                
                <!-- Diagrams Panel -->
                <div id="diagrams-panel" class="content-panel">
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
                
                <!-- Sessions Panel -->
                <div id="sessions-panel" class="content-panel">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card mb-4">
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
                            <div class="card mb-4">
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
            <footer class="pt-3 border-top text-center text-muted" style="padding: 1rem 2rem; font-size: 0.8rem;">
                <p><i class="fa fa-code"></i> RegCap GPT - Regulatory Document Analysis Platform | Version 1.0.0 | Made with <i class="fa fa-heart text-danger"></i> by RegCap Team</p>
            </footer>
        </div>
    </div>
    
    <script>
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize feature list toggle
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
            
            // Content navigation
            var navItems = document.querySelectorAll('.nav-item');
            var panelTitles = {
                'chat-panel': '<i class="fa fa-comments"></i> Chat with your Documents',
                'docs-panel': '<i class="fa fa-file-pdf-o"></i> Document Management',
                'diagrams-panel': '<i class="fa fa-sitemap"></i> Generated Diagrams',
                'sessions-panel': '<i class="fa fa-database"></i> Session Management'
            };
            
            // Add click event to each navigation item
            for (var i = 0; i < navItems.length; i++) {
                navItems[i].addEventListener('click', function() {
                    // If this is the features toggle, don't navigate
                    if (this.id === 'featureToggle') {
                        return;
                    }
                    
                    // Get the panel id from data-panel attribute
                    var panelId = this.getAttribute('data-panel');
                    if (!panelId) return;
                    
                    // Hide all content panels
                    var contentPanels = document.querySelectorAll('.content-panel');
                    for (var j = 0; j < contentPanels.length; j++) {
                        contentPanels[j].classList.remove('active');
                    }
                    
                    // Remove active class from all navigation items
                    for (var k = 0; k < navItems.length; k++) {
                        navItems[k].classList.remove('active');
                    }
                    
                    // Show the selected content panel
                    var panelElement = document.getElementById(panelId);
                    if (panelElement) {
                        panelElement.classList.add('active');
                    }
                    
                    // Update panel title
                    if (panelTitles[panelId]) {
                        document.getElementById('currentPanelTitle').innerHTML = panelTitles[panelId];
                    }
                    
                    // Add active class to clicked navigation item
                    this.classList.add('active');
                });
            }
            
            // Theme toggle functionality
            function setupThemeToggle() {
                var themeToggle = document.getElementById('mobileThemeToggle');
                var savedTheme = localStorage.getItem('theme');
                
                // Apply saved theme
                if (savedTheme === 'dark') {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    if (themeToggle) {
                        themeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                    }
                }
                
                // Toggle theme on click
                if (themeToggle) {
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
                }
            }
            
            // Initialize theme toggle
            setupThemeToggle();
            
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
                        processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <i class="fa fa-spinner fa-spin"></i> Processing your question...';
                        chatMessages.appendChild(processingDiv);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        // Send question to the server
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
                                var questionId = data.question_id;
                                
                                // Poll for status updates
                                var pollInterval = setInterval(function() {
                                    fetch('/question-status/' + questionId)
                                        .then(response => response.json())
                                        .then(status => {
                                            if (status.done) {
                                                clearInterval(pollInterval);
                                                
                                                if (status.error) {
                                                    processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error: ' + status.error + '</span>';
                                                } else {
                                                    // Format the answer with markdown
                                                    processingDiv.innerHTML = '<strong>RegCap GPT:</strong> ' + status.answer;
                                                    
                                                    // If there's a diagram, display it
                                                    if (status.has_diagram) {
                                                        var diagramDiv = document.createElement('div');
                                                        diagramDiv.className = 'bot-message diagram-message';
                                                        
                                                        // Make sure we have a clean diagram code (escape any HTML)
                                                        var diagramCode = status.diagram_code
                                                            .replace(/&/g, '&amp;')
                                                            .replace(/</g, '&lt;')
                                                            .replace(/>/g, '&gt;')
                                                            .replace(/"/g, '&quot;')
                                                            .replace(/'/g, '&#039;');
                                                            
                                                        // Create diagram container with unique ID
                                                        var diagramId = 'diagram_' + new Date().getTime();
                                                        diagramDiv.innerHTML = '<strong>Diagram:</strong> <div id="' + diagramId + '" class="mermaid mermaid-container">' + diagramCode + '</div>';
                                                        chatMessages.appendChild(diagramDiv);
                                                        
                                                        // Initialize mermaid with retry mechanism
                                                        setTimeout(function() {
                                                            try {
                                                                if (typeof mermaid !== 'undefined') {
                                                                    console.log("Rendering diagram with code:", diagramCode);
                                                                    mermaid.init(undefined, '#' + diagramId);
                                                                    
                                                                    // Add error-checking timeout to catch rendering failures
                                                                    setTimeout(function() {
                                                                        var diagramElement = document.getElementById(diagramId);
                                                                        if (diagramElement && diagramElement.innerHTML.includes("Syntax error")) {
                                                                            console.log("Detected mermaid syntax error, showing fallback");
                                                                            // Clean up the error message and show the diagram code
                                                                            diagramElement.innerHTML = 
                                                                                '<div class="alert alert-warning">The diagram could not be rendered due to syntax issues.</div>' +
                                                                                '<pre style="background-color:#f8f9fa; padding:10px; border-radius:5px;">' + 
                                                                                diagramCode + '</pre>';
                                                                        }
                                                                    }, 1000);
                                                                }
                                                            } catch (e) {
                                                                console.error("Error rendering diagram:", e);
                                                                // Fallback to simple display
                                                                document.getElementById(diagramId).innerHTML = 
                                                                    '<div class="alert alert-danger">Error rendering diagram</div>' +
                                                                    '<pre style="background-color:#f8f9fa; padding:10px; border-radius:5px;">' + 
                                                                    diagramCode + '</pre>';
                                                            }
                                                        }, 500); // Small delay to ensure the DOM is updated
                                                    }
                                                }
                                                
                                                chatMessages.scrollTop = chatMessages.scrollHeight;
                                            } else if (status.stage && status.progress) {
                                                // Update the processing message with the current status
                                                processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <i class="fa fa-spinner fa-spin"></i> ' + 
                                                                         status.stage + ' (' + status.progress + '%)';
                                            }
                                        })
                                        .catch(error => {
                                            console.error('Error polling question status:', error);
                                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error checking question status. Please try again.</span>';
                                            clearInterval(pollInterval);
                                        });
                                }, 1000); // Poll every second
                            } else {
                                processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error: ' + (data.error || 'Failed to process question') + '</span>';
                            }
                        })
                        .catch(error => {
                            console.error('Error submitting question:', error);
                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span class="text-danger">Error submitting question. Please try again.</span>';
                        });
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
                        // Show loading message
                        var uploadBtn = this.querySelector('button[type="submit"]');
                        var originalBtnText = uploadBtn.innerHTML;
                        uploadBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Processing...';
                        uploadBtn.disabled = true;
                        
                        // Create FormData and append files
                        var formData = new FormData();
                        for (var i = 0; i < fileInput.files.length; i++) {
                            formData.append('files', fileInput.files[i]);
                        }
                        
                        // Send files to the server
                        fetch('/upload-files', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert('Files successfully processed: ' + data.message);
                                // Reload page to refresh the documents list
                                window.location.reload();
                            } else {
                                alert('Error: ' + data.error);
                                // Reset button
                                uploadBtn.innerHTML = originalBtnText;
                                uploadBtn.disabled = false;
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            alert('An error occurred while uploading the files.');
                            // Reset button
                            uploadBtn.innerHTML = originalBtnText;
                            uploadBtn.disabled = false;
                        });
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
                        // Create a new session via API
                        fetch('/new-session', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert('New session created successfully!');
                                window.location.reload();
                            } else {
                                alert('Error: ' + data.error);
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            alert('An error occurred while creating a new session.');
                        });
                    }
                });
            }
            
            // Session switch buttons
            var sessionSwitchBtns = document.querySelectorAll('.session-switch-btn');
            for (var s = 0; s < sessionSwitchBtns.length; s++) {
                sessionSwitchBtns[s].addEventListener('click', function() {
                    var sessionId = this.getAttribute('data-session-id');
                    if (confirm('Switch to session ' + sessionId + '?')) {
                        // Switch to the selected session via API
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
                                alert('Error: ' + data.error);
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            alert('An error occurred while switching sessions.');
                        });
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
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'})
            
        # Store the session ID in the Flask session
        session['current_session'] = session_id
        
        return jsonify({
            'success': True, 
            'message': f'Switched to session {session_id}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Define upload folder
UPLOAD_FOLDER = 'data_storage'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/upload-files', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    try:
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'No files selected'})
        
        session_id = get_current_session()
        processed_files = []
        
        for file in files:
            if file and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Extract text from PDF
                try:
                    chunks = extract_text_from_pdf(file_path)
                    
                    # Store document chunks
                    save_document_chunks(filename, chunks)
                    processed_files.append(filename)
                except Exception as pdf_error:
                    return jsonify({
                        'success': False, 
                        'error': f"Error processing PDF {filename}: {str(pdf_error)}"
                    })
        
        return jsonify({
            'success': True, 
            'message': f'Processed {len(processed_files)} files', 
            'files': processed_files
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ask-question', methods=['POST'])
def ask_question():
    """Handle questions from the user."""
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})
            
        # Generate a unique ID for this question
        question_id = f"q_{time.time()}"
        
        # Initialize the status record for this question
        update_question_status(question_id, stage="Starting", progress=0)
        
        # Start a background thread to process the question
        thread = threading.Thread(
            target=process_question,
            args=(question, question_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'question_id': question_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
        
def process_question(question, question_id):
    """Process a question in the background."""
    try:
        session_id = get_current_session()
        
        # Update status: Retrieving documents
        update_question_status(question_id, stage="Retrieving documents", progress=10)
        
        # Get document chunks for the current session
        chunks = get_document_chunks(session_id)
        
        if not chunks:
            update_question_status(
                question_id, 
                stage="Error", 
                progress=100, 
                done=True, 
                error="No documents found. Please upload a document first."
            )
            return
            
        # Flatten chunks into a list
        all_chunks = []
        for doc_name, doc_chunks in chunks.items():
            print(f"Processing document: {doc_name}")
            print(f"Document chunks type: {type(doc_chunks)}")
            if doc_chunks and len(doc_chunks) > 0:
                print(f"First chunk type: {type(doc_chunks[0])}")
                print(f"First chunk sample: {str(doc_chunks[0])[:100]}")
            
            for i, chunk in enumerate(doc_chunks):
                # Add source metadata
                try:
                    # Handle different types of chunks
                    if isinstance(chunk, dict) and "content" in chunk:
                        # Already has metadata
                        all_chunks.append(chunk)
                    else:
                        # Add metadata
                        chunk_with_metadata = {
                            "content": str(chunk),
                            "metadata": {
                                "source": doc_name,
                                "page": f"{i//5 + 1}"  # Estimate page numbers - 5 chunks per page
                            }
                        }
                        all_chunks.append(chunk_with_metadata)
                except Exception as e:
                    print(f"Error processing chunk {i}: {str(e)}")
                    
        print(f"Total processed chunks: {len(all_chunks)}")
        if all_chunks and len(all_chunks) > 0:
            print(f"First processed chunk: {str(all_chunks[0])[:100]}")
        
        # Update status: Analyzing question
        update_question_status(question_id, stage="Analyzing question", progress=30)
        
        # Check if this is a diagram request
        is_diagram, diagram_type = detect_diagram_request(question)
        
        # Update status: Generating response
        update_question_status(
            question_id, 
            stage=f"{'Generating diagram' if is_diagram else 'Generating answer'}", 
            progress=50
        )
        
        if is_diagram:
            # Generate a diagram
            success, result = generate_diagram(question, all_chunks, diagram_type)
            
            if success:
                # Extract diagram code and explanation
                original_diagram_code = result["diagram_code"]
                explanation = result["explanation"]
                
                # Fix Mermaid syntax for better compatibility
                try:
                    # First try to fix with our utility function
                    diagram_code = fix_mermaid_syntax(original_diagram_code, diagram_type)
                    
                    # Add additional aggressive fixing for troublesome diagrams
                    # Only use the ISO 20022 template if specifically requested
                    if diagram_type == "flowchart" and ("ISO 20022" in question or "ISO20022" in question):
                        # Use a simplified Mermaid diagram with proper formatting for ISO 20022
                        diagram_code = """graph TD
    A(ISO 20022) --> B(Value Proposition)
    A --> C(Standardization Approach)
    A --> D(ISO 20022 Recipe)
    A --> E(Actors)
    A --> F(Financial Repository)
    
    B --> B1(Communication Interoperability)
    B --> B2(Address Overlapping Standards)
    
    C --> C1(Single Standard Long-term)
    C --> C2(Coexistence Short-term)
    
    D --> D1(Modeling-based Standards)
    D --> D2(Development Process)
    D --> D3(Registration)
    
    E --> E1(Registration Management Group)
    E --> E2(Standards Evaluation Groups)
    E --> E3(Registration Authority)
    
    F --> F1(Data Dictionary)
    F --> F2(Business Process Catalogue)"""
                    # For general error handling without using hardcoded templates
                    elif "syntax error" in explanation.lower() or diagram_code.strip() == "":
                        # Create a simplified fallback diagram based on the question
                        # Extract key terms from the question for a generic diagram
                        terms = [word for word in question.split() if len(word) > 3 and word.lower() not in ["show", "create", "diagram", "visualization", "flowchart", "about", "explain"]]
                        
                        # Use the top 3-5 unique terms for a simple diagram
                        unique_terms = list(set(terms))[:5] 
                        
                        # Start with a basic diagram structure
                        diagram_code = "graph TD\n"
                        
                        # Create a root node with the main topic
                        root_term = "Main_Topic"
                        if len(unique_terms) > 0:
                            root_term = unique_terms[0]
                        
                        diagram_code += f"    A({root_term})\n"
                        
                        # Add branches based on other extracted terms
                        for i, term in enumerate(unique_terms[1:], 1):
                            node_id = chr(65 + i)  # B, C, D, etc.
                            diagram_code += f"    {node_id}({term})\n"
                            diagram_code += f"    A --> {node_id}\n"
                            
                    print(f"Original diagram code: {original_diagram_code[:50]}...")
                    print(f"Fixed diagram code: {diagram_code[:50]}...")
                except Exception as e:
                    print(f"Error fixing diagram: {str(e)}")
                    # Fallback to simplest possible diagram based on the question
                    # Extract main topic from question
                    question_words = question.replace("?", "").replace(".", "").split()
                    main_topic = "Topic"
                    
                    # Get the most significant words from the question (avoiding common words)
                    significant_words = [word for word in question_words if len(word) > 3 and word.lower() not in ["show", "create", "diagram", "about", "explain", "visualization", "flowchart"]]
                    
                    if significant_words:
                        main_topic = significant_words[0]
                        
                    # Create a simple fallback diagram
                    diagram_code = f"graph TD\nA({main_topic}) --> B(Concept)\nA --> C(Element)\nB --> D(Details)"
                
                # Save the diagram
                # save_diagram(diagram_code, explanation, diagram_type)
                
                # Update status as complete with diagram
                update_question_status(
                    question_id,
                    stage="Complete",
                    progress=100,
                    done=True,
                    answer=explanation,
                    has_diagram=True,
                    diagram_code=diagram_code
                )
                
                # Save to chat history
                save_chat_history(question, explanation)
            else:
                # Update status with error
                update_question_status(
                    question_id,
                    stage="Error",
                    progress=100,
                    done=True,
                    error=f"Failed to generate diagram: {result}"
                )
        else:
            # Generate a text answer
            answer = generate_answer(question, all_chunks)
            
            # Update status as complete with answer
            update_question_status(
                question_id,
                stage="Complete",
                progress=100,
                done=True,
                answer=answer
            )
            
            # Save to chat history
            save_chat_history(question, answer)
            
    except Exception as e:
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
    app.run(host='0.0.0.0', port=5000)