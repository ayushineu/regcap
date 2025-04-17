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

# Standard library imports
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, session
import os
import time
import pickle
import base64
import uuid
import json
import threading
import re

# Third-party library imports
import PyPDF2
import openai
import numpy as np
import faiss
from werkzeug.utils import secure_filename

# Local application imports
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

# Create our own question status tracking system independent of flask_app
question_status_store = {}

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
            /* Main colors */
            --primary-color: #2563eb;        /* More blue for primary actions */
            --primary-hover: #1e40af;        /* Darker blue on hover */
            --secondary-color: #475569;      /* Slate for secondary elements */
            --accent-color: #f59e0b;         /* Amber for accent/notifications */
            
            /* Background colors */
            --primary-bg: #ffffff;           /* Clean white background */
            --secondary-bg: #f1f5f9;         /* Light gray secondary background */
            --tertiary-bg: #e2e8f0;          /* Slightly darker for cards/sections */
            
            /* Text colors */
            --primary-text: #0f172a;         /* Dark slate for main text */
            --secondary-text: #475569;       /* Medium slate for secondary text */
            --light-text: #f8fafc;           /* Almost white for dark backgrounds */
            
            /* Borders */
            --border-color: #cbd5e1;         /* Light border for light theme */
            --border-radius: 8px;            /* Consistent roundness */
            
            /* Shadows */
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
            
            /* Button colors for consistency */
            --primary-btn: var(--primary-color);
            --primary-btn-hover: var(--primary-hover);
        }
        
        [data-theme="dark"] {
            /* Main colors for dark theme */
            --primary-color: #3b82f6;        /* Brighter blue for dark theme */
            --primary-hover: #60a5fa;        /* Lighter blue on hover for dark theme */
            --secondary-color: #94a3b8;      /* Lighter slate for dark theme */
            --accent-color: #fbbf24;         /* Brighter amber for dark theme */
            
            /* Background colors */
            --primary-bg: #0f172a;           /* Dark slate background */
            --secondary-bg: #1e293b;         /* Slightly lighter background */
            --tertiary-bg: #334155;          /* Even lighter for cards/sections */
            
            /* Text colors */
            --primary-text: #f1f5f9;         /* Light text on dark background */
            --secondary-text: #cbd5e1;       /* Slightly darker for secondary text */
            --light-text: #ffffff;           /* Pure white for emphasis */
            
            /* Borders */
            --border-color: #475569;         /* Darker border for dark theme */
            
            /* Button colors for consistency */
            --primary-btn: var(--primary-color);
            --primary-btn-hover: var(--primary-hover);
        }
        
        body {
            background-color: var(--primary-bg);
            color: var(--primary-text);
            transition: all 0.3s ease;
            margin: 0;
            padding: 0;
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.5;
        }
        
        /* Global rounded corners and shadows */
        .card, .btn, .form-control, .alert, .list-group-item,
        .tab-content, .chat-container, .diagram-container, .explanation-card {
            border-radius: var(--border-radius) !important;
            overflow: hidden;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Modern header with accent gradient */
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
            letter-spacing: -0.5px;
        }
        
        /* Improved tab container with better spacing */
        .tab-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 220px);
            background-color: var(--secondary-bg);
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }
        
        /* Enhanced tab buttons */
        .tab-buttons {
            display: flex;
            background-color: var(--tertiary-bg);
            padding: 0.75rem;
            gap: 0.5rem;
            border-bottom: none;
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
            transform: translateY(-2px);
        }
        
        .tab-button.active {
            background-color: var(--primary-btn);
            color: var(--light-text);
            box-shadow: var(--shadow-md);
        }
        
        .tab-content {
            display: none;
            padding: 2rem;
            background-color: var(--primary-bg);
            flex-grow: 1;
            overflow-y: auto;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Modern section titles */
        .tab-content h2 {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* Enhanced chat container */
        .chat-container {
            height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            background-color: var(--secondary-bg);
            box-shadow: var(--shadow-sm);
        }
        
        /* Modern message bubbles */
        .user-message, .bot-message {
            padding: 1rem 1.25rem;
            margin: 0.75rem 0;
            border-radius: 1rem;
            max-width: 85%;
            box-shadow: var(--shadow-sm);
            line-height: 1.5;
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
        
        .user-message strong, .bot-message strong {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            opacity: 0.9;
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
        /* Enhanced diagram styling */
        .diagram-container {
            padding: 2rem;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            margin: 1.5rem 0;
            overflow-x: auto;
            background-color: var(--secondary-bg);
            box-shadow: var(--shadow-md);
        }
        
        .svg-container {
            width: 100%;
            overflow-x: auto;
            padding: 1rem;
            background-color: var(--primary-bg);
            border-radius: var(--border-radius);
        }
        
        .error-container {
            margin: 1rem 0;
            padding: 1rem;
            background-color: rgba(var(--accent-color), 0.1);
            border-radius: var(--border-radius);
            border-left: 4px solid var(--accent-color);
            display: none;
        }
        
        .mermaid svg {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
        }
        
        /* Improved explanation card */
        .explanation-container, .explanation-card {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-sm);
            color: var(--primary-text);
        }
        
        .explanation-container h4, .explanation-card h4 {
            color: var(--primary-color);
            margin-bottom: 1rem;
            font-weight: 700;
            font-size: 1.2rem;
        }
        
        .explanation-container p, .explanation-card p, .explanation-text {
            color: var(--primary-text);
            font-size: 1rem;
            line-height: 1.6;
        }
        
        /* Card styling for diagrams */
        .card {
            border: none;
            box-shadow: var(--shadow-md);
            margin-bottom: 2.5rem;
            overflow: hidden;
        }
        
        .card-header {
            background: linear-gradient(to right, var(--primary-color), var(--primary-hover));
            padding: 1.25rem;
            border: none;
        }
        
        .card-header h3 {
            color: var(--light-text);
            font-weight: 600;
            letter-spacing: -0.01em;
        }
        
        .card-body {
            padding: 1.5rem;
            background-color: var(--primary-bg);
        }
        
        /* Diagram tab buttons */
        .diagram-tab-row {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }
        
        .diagram-tab-btn {
            padding: 0.75rem 1.25rem;
            background-color: var(--secondary-bg);
            color: var(--secondary-text);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
        }
        
        .diagram-tab-btn:hover {
            background-color: var(--tertiary-bg);
            transform: translateY(-2px);
        }
        
        .diagram-tab-btn.active {
            background-color: var(--primary-btn);
            color: var(--light-text);
            border-color: var(--primary-hover);
        }
        
        /* Code container */
        .code-container {
            background-color: var(--tertiary-bg);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-top: 1rem;
        }
        
        .code-container pre {
            font-family: 'Consolas', 'Monaco', monospace;
            white-space: pre-wrap;
            color: var(--primary-text);
        }
        
        .text-dark {
            color: #212529 !important;
        }
        
        [data-theme="dark"] .text-dark {
            color: #e0e0e0 !important;
        }
        
        /* Enhanced button styles */
        .btn {
            padding: 0.75rem 1.5rem;
            font-weight: 500;
            transition: all 0.2s ease;
            border: none;
            box-shadow: var(--shadow-sm);
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
            color: var(--light-text);
        }
        
        .btn-primary:hover, .btn-primary:focus {
            background: linear-gradient(135deg, var(--primary-hover), var(--primary-color));
        }
        
        .btn-outline-primary {
            background-color: transparent;
            color: var(--primary-color);
            border: 1px solid var(--primary-color);
        }
        
        .btn-outline-primary:hover, .btn-outline-primary:focus {
            background-color: var(--primary-color);
            color: var(--light-text);
        }
        
        /* Enhanced form controls */
        .form-control {
            padding: 0.75rem 1rem;
            border: 1px solid var(--border-color);
            background-color: var(--primary-bg);
            color: var(--primary-text);
            transition: all 0.2s ease;
        }
        
        .form-control:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 0.25rem rgba(37, 99, 235, 0.25);
        }
        
        textarea.form-control {
            min-height: 120px;
            line-height: 1.6;
        }
        
        .form-label {
            font-weight: 500;
            color: var(--primary-text);
            margin-bottom: 0.5rem;
        }
        
        /* Dark mode toggle */
        #darkModeToggle {
            background-color: var(--tertiary-bg);
            color: var(--primary-text);
            border: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.6rem 1.2rem;
            transition: all 0.2s ease;
        }
        
        #darkModeToggle:hover {
            background-color: var(--primary-hover);
            color: var(--light-text);
        }
        
        /* Status alerts */
        .alert {
            border: none;
            border-radius: var(--border-radius);
            padding: 1rem 1.25rem;
            margin-top: 1.5rem;
            box-shadow: var(--shadow-sm);
        }
        
        .alert-info {
            background-color: rgba(37, 99, 235, 0.1);
            color: var(--primary-color);
            border-left: 4px solid var(--primary-color);
        }
        
        .alert-secondary {
            background-color: var(--secondary-bg);
            color: var(--secondary-text);
            border-left: 4px solid var(--secondary-color);
        }
        
        /* List group styling */
        .list-group-item {
            padding: 1rem 1.25rem;
            background-color: var(--primary-bg);
            border: 1px solid var(--border-color);
            color: var(--primary-text);
            transition: all 0.2s ease;
        }
        
        .list-group-item:hover {
            background-color: var(--secondary-bg);
        }
        
        /* Badges */
        .badge {
            padding: 0.5rem 0.75rem;
            font-weight: 500;
            border-radius: 2rem;
        }
        
        .badge.bg-primary {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover)) !important;
        }
    /* Beta Banner Styles */
        .beta-banner {
            background-color: #fef3c7;
            color: #92400e;
            border-left: 4px solid #f59e0b;
            padding: 0.5rem 1rem;
            margin-bottom: 1rem;
            border-radius: var(--border-radius);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.875rem;
        }
        
        [data-theme="dark"] .beta-banner {
            background-color: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border-left: 4px solid #f59e0b;
        }
        
        .beta-banner-content {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .beta-close-btn {
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            font-size: 1.25rem;
            opacity: 0.7;
            transition: opacity 0.2s;
        }
        
        .beta-close-btn:hover {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Beta Banner -->
        <div id="betaBanner" class="beta-banner">
            <div class="beta-banner-content">
                <span style="font-size: 1rem;">🚧</span>
                <span><strong>Beta Notice:</strong> RegCap GPT is currently in active development. Some features may be limited or evolving.</span>
            </div>
            <button class="beta-close-btn" onclick="document.getElementById('betaBanner').style.display='none';">&times;</button>
        </div>
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
                            <div class="card-header bg-primary text-white">
                                <h3 class="m-0">{{ diagram_type|capitalize }} Diagram</h3>
                            </div>
                            <div class="card-body">
                                <div class="explanation-card p-3 mb-4 border rounded">
                                    <h4 class="mb-2 fw-bold">Explanation</h4>
                                    <p class="explanation-text">{{ explanation }}</p>
                                </div>
                                
                                <!-- Diagram Tabs -->
                                <div class="diagram-tab-row mt-5">
                                    <button class="diagram-tab-btn" data-parent-index="{{ loop.index0 }}" data-tab="generated">Generated Diagram</button>
                                    <button class="diagram-tab-btn active" data-parent-index="{{ loop.index0 }}" data-tab="simplified">Simplified Diagram</button>
                                    <button class="diagram-tab-btn" data-parent-index="{{ loop.index0 }}" data-tab="rawcode">Raw Code</button>
                                    <button class="diagram-tab-btn" data-parent-index="{{ loop.index0 }}" data-tab="fullpage">Full Page View</button>
                                </div>
                                
                                <!-- Tab Contents -->
                                <div id="generated-{{ loop.index0 }}" class="tab-content">
                                    <div class="diagram-container">
                                        <div class="mermaid diagram-display">{{ diagram_code }}</div>
                                        <div class="alert alert-warning diagram-error" style="display: none;">
                                            <i class="fa fa-exclamation-triangle"></i> 
                                            The generated diagram has syntax errors. Please use the simplified view by clicking the tab above.
                                        </div>
                                    </div>
                                </div>
                                
                                <div id="simplified-{{ loop.index0 }}" class="tab-content active">
                                    <div class="diagram-container">
                                        <div class="mermaid diagram-display simplified-diagram">
{% if diagram_type == "flowchart" %}
graph TD
    A(Start) --> B(ISO 20022 Process)
    B --> C(Identify Business Processes)
    C --> D(Define Message Models)
    D --> E(Implement Standard)
    E --> F(End)
{% elif diagram_type == "sequence" %}
sequenceDiagram
    participant User
    participant System
    User->>System: Submit Request
    System->>System: Process Request
    System->>User: Return Response
{% else %}
graph TD
    A(ISO 20022 Standard) --> B(Business Process)
    B --> C(Message Definition)
    C --> D(Implementation)
{% endif %}
                                        </div>
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
        /**
         * RegCap GPT - Main Application JavaScript
         * 
         * This script handles:
         * 1. Tab navigation and switching between main app sections
         * 2. Dark/light mode theme toggling with local storage persistence
         * 3. Question submission with AJAX and background processing
         * 4. Real-time status updates via polling
         * 5. Session management (creating new sessions and switching between them)
         * 6. Mermaid diagram rendering with error handling and fallbacks
         * 7. Diagram tab navigation within the diagram cards
         */
        document.addEventListener('DOMContentLoaded', function() {
            // ============================================================
            // MAIN NAVIGATION TAB SYSTEM
            // ============================================================
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
                    
                    // Special handling for diagram tab - render diagrams and clear notification
                    if (tabId === 'diagrams') {
                        var notificationDot = document.getElementById('diagramsNotification');
                        if (notificationDot) {
                            notificationDot.style.display = 'none';
                        }
                        renderAllDiagrams();
                    }
                };
            }
            
            // ============================================================
            // DARK MODE TOGGLE WITH LOCAL STORAGE PERSISTENCE
            // ============================================================
            var darkModeToggle = document.getElementById('darkModeToggle');
            if (darkModeToggle) {
                // Check saved preference from localStorage
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
            
            // ============================================================
            // QUESTION FORM HANDLING WITH AJAX SUBMISSION & STATUS POLLING
            // ============================================================
            var questionForm = document.getElementById('question-form');
            if (questionForm) {
                questionForm.onsubmit = function(e) {
                    e.preventDefault();
                    
                    var question = document.getElementById('question').value.trim();
                    if (!question) return;
                    
                    // Disable submit button to prevent multiple submissions
                    var submitButton = this.querySelector('button[type="submit"]');
                    submitButton.disabled = true;
                    
                    // Save the question text for potential page reloads
                    localStorage.setItem('lastQuestion', question);
                    
                    // Add user message to chat with visual formatting
                    var chatContainer = document.getElementById('chatMessages');
                    var userMessage = document.createElement('div');
                    userMessage.className = 'user-message';
                    userMessage.innerHTML = '<strong>You:</strong> ' + question;
                    chatContainer.appendChild(userMessage);
                    
                    // Add bot response placeholder with loading indicator
                    var botMessage = document.createElement('div');
                    botMessage.className = 'bot-message';
                    botMessage.innerHTML = '<strong>Bot:</strong> <span class="processing">Processing your question... <div class="spinner-border spinner-border-sm" role="status"></div></span>';
                    chatContainer.appendChild(botMessage);
                    
                    // Auto-scroll to bottom to show new messages
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    
                    // Prepare and submit the question via AJAX
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
                            // Update processing indicator text with simplified message
                            var processingSpan = document.querySelector('.processing');
                            if (processingSpan) {
                                processingSpan.innerHTML = "Processing your question... <div class='spinner-border spinner-border-sm' role='status'></div>";
                            }
                            
                            // Get the question ID returned from the server
                            var questionId = data.question_id;
                            
                            // Set up polling to check question processing status
                            var statusInterval = setInterval(function() {
                                fetch('/get_question_status/' + questionId)
                                    .then(function(response) { return response.json(); })
                                    .then(function(statusData) {
                                        if (statusData.done) {
                                            // Processing complete - clear interval and reload page
                                            clearInterval(statusInterval);
                                            // Small delay to ensure storage is fully saved
                                            setTimeout(function() {
                                                window.location.reload();
                                            }, 1000);
                                        } else if (statusData.stage) {
                                            // Update processing stage information
                                            var processingSpan = document.querySelector('.processing');
                                            if (processingSpan) {
                                                processingSpan.innerHTML = statusData.stage + "... <div class='spinner-border spinner-border-sm' role='status'></div>";
                                            }
                                        }
                                    })
                                    .catch(function(error) {
                                        console.error('Error checking status:', error);
                                    });
                            }, 2000); // Poll every 2 seconds
                        } else {
                            // Handle error from the server
                            alert('Error: ' + (data.error || 'Unknown error'));
                            submitButton.disabled = false;
                        }
                    })
                    .catch(function(error) {
                        // Handle network or other errors
                        console.error('Error:', error);
                        alert('Error processing request');
                        submitButton.disabled = false;
                    });
                    
                    // Clear the input field after submission
                    document.getElementById('question').value = '';
                };
            }
            
            // ============================================================
            // SESSION MANAGEMENT
            // ============================================================
            
            // Create new session button
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
            
            // Switch between sessions buttons
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
            
            // ============================================================
            // DIAGRAM RENDERING WITH ERROR HANDLING
            // ============================================================
            
            /**
             * Render all Mermaid diagrams with error handling and fallbacks
             * If a diagram fails to render, it will show an error message
             * and automatically switch to a simplified version
             */
            function renderAllDiagrams() {
                var diagrams = document.querySelectorAll('.mermaid');
                var errorCount = 0;
                
                for (var i = 0; i < diagrams.length; i++) {
                    var diagram = diagrams[i];
                    var diagramContainer = diagram.closest('.diagram-container');
                    var errorContainer = diagramContainer.querySelector('.diagram-error');
                    
                    try {
                        // Use the safer render method with callback for better error handling
                        var id = 'diagram-' + Math.random().toString(36).substring(2, 8);
                        mermaid.render(id, diagram.textContent, function(svgCode) {
                            diagram.innerHTML = svgCode;
                            // Hide error message if successful
                            if (errorContainer) {
                                errorContainer.style.display = 'none';
                            }
                        });
                    } catch (e) {
                        // Show error message when rendering fails
                        console.error('Error rendering diagram:', e);
                        errorCount++;
                        if (errorContainer) {
                            errorContainer.style.display = 'block';
                        }
                        
                        // Auto-switch to the simplified view for this diagram
                        var card = diagram.closest('.card');
                        if (card) {
                            var simplifiedTab = card.querySelector('[data-tab="simplified"]');
                            if (simplifiedTab) {
                                setTimeout(function() {
                                    simplifiedTab.click();
                                }, 500);
                            }
                        }
                    }
                }
                
                // Log warning if all diagrams had rendering errors
                if (errorCount > 0 && errorCount === diagrams.length) {
                    console.warn('All diagrams had rendering errors');
                }
            }
            
            // ============================================================
            // DIAGRAM TAB NAVIGATION WITHIN CARDS
            // ============================================================
            
            // Handle clicking on diagram tabs within each diagram card
            var diagramTabBtns = document.querySelectorAll('.diagram-tab-row .diagram-tab-btn');
            for (var i = 0; i < diagramTabBtns.length; i++) {
                diagramTabBtns[i].addEventListener('click', function() {
                    var tabId = this.getAttribute('data-tab');
                    var parentIndex = this.getAttribute('data-parent-index');
                    
                    // Get the parent diagram card
                    var parentDiagramCard = this.closest('.card');
                    
                    // Hide all tab contents for this particular diagram
                    var tabContents = parentDiagramCard.querySelectorAll('.tab-content');
                    tabContents.forEach(function(content) {
                        content.classList.remove('active');
                    });
                    
                    // Deactivate all tabs for this diagram
                    var tabBtns = parentDiagramCard.querySelectorAll('.diagram-tab-btn');
                    tabBtns.forEach(function(btn) {
                        btn.classList.remove('active');
                    });
                    
                    // Activate clicked tab and its content
                    this.classList.add('active');
                    parentDiagramCard.querySelector('#' + tabId + '-' + parentIndex).classList.add('active');
                    
                    // Re-render mermaid diagram if needed when switching to simplified tab
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
            
            // ============================================================
            // MERMAID INITIALIZATION
            // ============================================================
            
            // Initialize Mermaid diagram library with compatible settings
            if (typeof mermaid !== 'undefined') {
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
                
                // Show notification dot if we have diagrams
                var hasDiagrams = document.querySelectorAll('.mermaid').length > 0;
                if (hasDiagrams) {
                    var notificationDot = document.getElementById('diagramsNotification');
                    if (notificationDot) {
                        notificationDot.style.display = 'block';
                    }
                }
            }
            
            // Clean up localStorage to prevent stale data
            localStorage.removeItem('lastQuestion');
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
        # STAGE 1: Duplicate Detection
        # Check if we already have this question in history to avoid duplicates and redundant processing
        current_history = get_chat_history()
        for q, _ in current_history:
            # Use exact string comparison (case-insensitive) to detect duplicate questions
            if question.lower().strip() == q.lower().strip():
                print(f"Duplicate question detected: '{question}' - skipping processing")
                return
        
        # Initialize status tracking for frontend updates
        update_question_status(question_id, stage="Starting", progress=0)
        
        # STAGE 2: Document Retrieval
        # Get all document chunks from the knowledge base
        chunks = get_all_document_chunks()
        if not chunks:
            # Handle the case where no documents have been uploaded
            answer = "Please upload some documents first. I don't have any knowledge base to work with yet."
            save_chat_history(question, answer)
            update_question_status(question_id, stage="Complete", progress=100, done=True)
            return
        
        # STAGE 3: Request Type Detection
        # Determine if the user wants a diagram or a text answer
        is_diagram_request, diagram_type = detect_diagram_request(question)
        
        # STAGE 4: Vector Store Creation
        # Create semantic vector embeddings for all document chunks
        update_question_status(question_id, stage="Creating vector store", progress=20)
        vector_store = create_vector_store(chunks)
        
        # STAGE 5: Context Retrieval 
        # Find chunks similar to the question using vector similarity
        update_question_status(question_id, stage="Finding relevant information", progress=40)
        similar_chunks = get_similar_chunks(question, vector_store)
        
        # STAGE 6: Content Generation
        # Generate either a diagram or text answer based on the request type
        if is_diagram_request:
            # For diagram requests, generate a Mermaid diagram with explanation
            actual_diagram_type = diagram_type if diagram_type else "flowchart"
            update_question_status(question_id, 
                                  stage=f"Generating {actual_diagram_type} diagram", 
                                  progress=60)
            
            try:
                success, result = generate_diagram(question, similar_chunks, actual_diagram_type)
                
                if success:
                    # Process successful diagram generation
                    diagram_code, explanation = result
                    
                    # Apply syntax fixes for better compatibility
                    diagram_code = fix_mermaid_syntax(diagram_code, actual_diagram_type)
                    
                    # Create user-friendly response message
                    answer = f"I've created a {actual_diagram_type} diagram based on your request. Please click on the \"Diagrams\" tab above to view it."
                    
                    # Save the diagram to storage
                    save_diagram(diagram_code, explanation, actual_diagram_type)
                else:
                    # Handle case where diagram generation logic failed
                    answer = f"I couldn't generate a diagram: {result}"
            except Exception as e:
                # Handle exceptions during diagram generation
                error_msg = str(e)
                log_message(f"Error generating diagram: {error_msg}")
                answer = f"I had trouble creating the diagram. Error: {error_msg}"
        else:
            # For regular questions, generate a text answer
            update_question_status(question_id, stage="Generating answer", progress=60)
            answer = generate_answer(question, similar_chunks)
        
        # STAGE 7: Save Results
        # Store the question and answer in chat history
        update_question_status(question_id, stage="Saving results", progress=80)
        save_chat_history(question, answer)
        
        # STAGE 8: Completion
        # Mark processing as complete for the frontend
        update_question_status(question_id, stage="Complete", progress=100, done=True)
        
    except Exception as e:
        # Global exception handler for any errors in the processing pipeline
        error_msg = str(e)
        log_message(f"Error processing question: {error_msg}")
        update_question_status(question_id, stage="Error", error=error_msg, done=True)
        
        # Save error to chat history so the user sees it
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
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 5px;
        }
        
        /* New Button Style Diagram Tabs */
        .diagram-tab-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .diagram-tab-btn {
            padding: 10px 15px;
            background-color: #e9ecef;
            color: #212529;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
            min-width: 120px;
        }
        
        .diagram-tab-btn:hover {
            background-color: #007bff;
            color: white;
            transform: translateY(-2px);
        }
        
        .diagram-tab-btn.active {
            background-color: #007bff;
            color: white;
            font-weight: 600;
            box-shadow: 0 3px 6px rgba(0,0,0,0.15);
        }
        
        [data-theme="dark"] .diagram-tab-btn {
            background-color: #444;
            color: #f0f0f0;
        }
        
        [data-theme="dark"] .diagram-tab-btn:hover {
            background-color: #0066cc;
        }
        
        [data-theme="dark"] .diagram-tab-btn.active {
            background-color: #0066cc;
            color: white;
        }
        
        /* Legacy Tab Styles */
        .tab-item {
            margin-bottom: 5px;
            padding: 0.75rem 1.25rem;
            cursor: pointer;
            background-color: var(--secondary-bg);
            color: var(--primary-text);
            border: 1px solid var(--border-color);
            border-radius: 0.25rem;
            font-weight: 500;
            transition: all 0.2s ease;
            display: inline-block;
            text-align: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            position: relative;
            z-index: 1;
        }
        .tab-item:hover {
            background-color: var(--primary-btn);
            color: #fff;
            border-color: var(--primary-btn);
        }
        .tab-item.active {
            color: #fff;
            background-color: var(--primary-btn);
            border-color: var(--primary-btn);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-weight: 600;
        }
        
        [data-theme="dark"] .tab-item {
            background-color: #2c2c2c;
            color: #e0e0e0;
            border-color: #444;
        }
        
        [data-theme="dark"] .tab-item:hover {
            background-color: var(--primary-btn);
            color: #fff;
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
    global question_status_store
    
    if question_id in question_status_store:
        return jsonify(question_status_store[question_id])
    else:
        # If question not in storage, assume it's completed or there was an error
        return jsonify({"error": "Question not found", "done": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)