"""
RegCap GPT - Minimal UI Fix 

This is a simplified version with minimal JavaScript to ensure basic UI functionality.
"""

import os
import time
import uuid
import threading
import base64
import pickle
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory

# Initialize Flask application
app = Flask(__name__)
app.secret_key = 'regcap-secret-key'

# Session management
def get_current_session():
    """Get or create the current session ID."""
    if 'current_session' not in session:
        session['current_session'] = str(uuid.uuid4())[:8]
    return session['current_session']

def create_new_session():
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())[:8]
    session['current_session'] = session_id
    return session_id

# Data structures for storage
question_statuses = {}
sessions = {}

@app.route('/')
def index():
    """Render the main application page."""
    session_id = get_current_session()
    
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegCap GPT</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f8f9fa;
        }
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .nav-tabs .nav-link {
            color: #495057;
        }
        .nav-tabs .nav-link.active {
            font-weight: 600;
            color: #0088cc;
            border-bottom: 2px solid #0088cc;
        }
        .chat-container {
            height: 60vh;
            overflow-y: auto;
            padding: 15px;
            background-color: #ffffff;
            border-radius: 0.25rem;
            border: 1px solid #dee2e6;
        }
        .user-message {
            background-color: #e9f5ff;
            padding: 10px 15px;
            border-radius: 15px 15px 15px 0;
            margin-bottom: 15px;
            max-width: 80%;
            align-self: flex-start;
        }
        .bot-message {
            background-color: #f0f0f0;
            padding: 10px 15px;
            border-radius: 15px 15px 0 15px;
            margin-bottom: 15px;
            max-width: 80%;
            align-self: flex-end;
            margin-left: auto;
        }
        .message-container {
            display: flex;
            flex-direction: column;
        }
        .app-header {
            background-color: #0088cc;
            color: white;
            padding: 15px 0;
        }
        .beta-notice {
            background-color: #ffeeba;
            border-left: 4px solid #ffc107;
            padding: 10px 15px;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }
        .document-list {
            margin-top: 15px;
        }
        .document-item {
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
        }
        .document-icon {
            color: #dc3545;
            margin-right: 10px;
        }
        .diagram-container {
            margin-top: 15px;
            padding: 15px;
            background-color: #ffffff;
            border-radius: 0.25rem;
            border: 1px solid #dee2e6;
        }
        .mermaid-container {
            padding: 15px;
            background-color: #f8f9fa;
            margin-top: 10px;
            border-radius: 4px;
        }
        .session-list {
            margin-top: 15px;
        }
        .btn-primary {
            background-color: #0088cc;
            border-color: #0088cc;
        }
        .btn-primary:hover {
            background-color: #006699;
            border-color: #006699;
        }
    </style>
</head>
<body>
    <header class="app-header">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-6">
                    <h1 class="mb-0">RegCap GPT</h1>
                    <p class="mb-0">Regulatory Intelligence</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <span class="d-inline-block me-3">Session: Test-Session</span>
                </div>
            </div>
        </div>
    </header>

    <div class="container mt-3">
        <div class="beta-notice">
            🚧 Beta Notice: RegCap GPT is currently in active development. Some features may be limited or evolving. Thank you for testing and sharing feedback!
        </div>
    </div>

    <div class="container main-container">
        <div class="row">
            <!-- Left Sidebar - Navigation -->
            <div class="col-md-3 mb-4">
                <div class="card">
                    <div class="card-header">
                        Navigation
                    </div>
                    <div class="list-group list-group-flush">
                        <a href="#chat-tab" class="list-group-item list-group-item-action active" data-bs-toggle="tab" role="tab" aria-controls="chat" aria-selected="true">
                            <i class="fas fa-comments me-2"></i> Chat
                        </a>
                        <a href="#documents-tab" class="list-group-item list-group-item-action" data-bs-toggle="tab" role="tab" aria-controls="documents" aria-selected="false">
                            <i class="fas fa-file-pdf me-2"></i> Documents
                        </a>
                        <a href="#diagrams-tab" class="list-group-item list-group-item-action" data-bs-toggle="tab" role="tab" aria-controls="diagrams" aria-selected="false">
                            <i class="fas fa-project-diagram me-2"></i> Diagrams
                        </a>
                        <a href="#sessions-tab" class="list-group-item list-group-item-action" data-bs-toggle="tab" role="tab" aria-controls="sessions" aria-selected="false">
                            <i class="fas fa-layer-group me-2"></i> Sessions
                        </a>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header">
                        Session Actions
                    </div>
                    <div class="card-body">
                        <button id="newSessionBtn" class="btn btn-primary btn-sm w-100 mb-2">
                            <i class="fas fa-plus-circle me-1"></i> New Session
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Main Content Area -->
            <div class="col-md-9">
                <div class="tab-content">
                    <!-- Chat Tab -->
                    <div class="tab-pane fade show active" id="chat-tab" role="tabpanel" aria-labelledby="chat-tab">
                        <div class="card">
                            <div class="card-header">
                                <i class="fas fa-comments me-2"></i> Chat
                            </div>
                            <div class="card-body">
                                <div class="chat-container" id="chatMessages">
                                    <div class="message-container">
                                        <div class="bot-message">
                                            <strong>RegCap GPT:</strong> Welcome to RegCap GPT! I'm here to help you understand regulatory documents. Please upload a document and ask questions about its content.
                                        </div>
                                    </div>
                                </div>
                                
                                <form id="questionForm" class="mt-3">
                                    <div class="input-group">
                                        <input type="text" id="userQuestion" class="form-control" placeholder="Ask a question about your documents...">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="fas fa-paper-plane"></i> Send
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Documents Tab -->
                    <div class="tab-pane fade" id="documents-tab" role="tabpanel" aria-labelledby="documents-tab">
                        <div class="card">
                            <div class="card-header">
                                <i class="fas fa-file-pdf me-2"></i> Documents
                            </div>
                            <div class="card-body">
                                <form id="uploadForm" enctype="multipart/form-data">
                                    <div class="mb-3">
                                        <label for="documentUpload" class="form-label">Upload Regulatory Documents</label>
                                        <input class="form-control" type="file" id="documentUpload" multiple accept=".pdf">
                                        <div class="form-text">Select one or more PDF files to upload.</div>
                                    </div>
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-upload me-1"></i> Upload Documents
                                    </button>
                                </form>
                                
                                <hr>
                                
                                <h5>Uploaded Documents</h5>
                                <div id="documentList" class="document-list">
                                    <p class="text-muted">No documents uploaded yet.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Diagrams Tab -->
                    <div class="tab-pane fade" id="diagrams-tab" role="tabpanel" aria-labelledby="diagrams-tab">
                        <div class="card">
                            <div class="card-header">
                                <i class="fas fa-project-diagram me-2"></i> Diagrams
                            </div>
                            <div class="card-body">
                                <p>Ask for diagrams in the chat to visualize regulatory concepts and processes. Your generated diagrams will appear here.</p>
                                <div id="diagramsList">
                                    <p class="text-muted">No diagrams generated yet.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Sessions Tab -->
                    <div class="tab-pane fade" id="sessions-tab" role="tabpanel" aria-labelledby="sessions-tab">
                        <div class="card">
                            <div class="card-header">
                                <i class="fas fa-layer-group me-2"></i> Sessions
                            </div>
                            <div class="card-body">
                                <p>Sessions help you organize different research contexts. Each session has its own set of documents and chat history.</p>
                                
                                <h5>Current Session</h5>
                                <p><strong>ID:</strong> <span class="badge bg-primary">test-session</span></p>
                                
                                <h5>Available Sessions</h5>
                                <div id="sessionsList" class="session-list">
                                    <p class="text-muted">No other sessions available.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@8.14.0/dist/mermaid.min.js"></script>
    <script>
        // Initialize Bootstrap components
        var triggerTabList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tab"]'));
        triggerTabList.forEach(function(triggerEl) {
            var tabTrigger = new bootstrap.Tab(triggerEl);
            
            triggerEl.addEventListener('click', function(event) {
                event.preventDefault();
                tabTrigger.show();
            });
        });
        
        // Initialize Mermaid
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {
                htmlLabels: true,
                curve: 'linear'
            }
        });
        
        // Wait for DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', function() {
            // Question form handling
            var questionForm = document.getElementById('questionForm');
            if (questionForm) {
                questionForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    var questionInput = document.getElementById('userQuestion');
                    var question = questionInput.value.trim();
                    
                    if (question) {
                        // Display user's question in chat
                        var chatMessages = document.getElementById('chatMessages');
                        var userMessageDiv = document.createElement('div');
                        userMessageDiv.className = 'message-container';
                        userMessageDiv.innerHTML = '<div class="user-message"><strong>You:</strong> ' + question + '</div>';
                        chatMessages.appendChild(userMessageDiv);
                        
                        // Add a processing message
                        var processingDiv = document.createElement('div');
                        processingDiv.className = 'message-container';
                        processingDiv.innerHTML = '<div class="bot-message"><strong>RegCap GPT:</strong> <i class="fa fa-spinner fa-spin"></i> Processing your question...</div>';
                        chatMessages.appendChild(processingDiv);
                        
                        // Scroll to bottom of chat
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        // Clear input
                        questionInput.value = '';
                        
                        // In this simplified version, we'll just show a sample response
                        setTimeout(function() {
                            processingDiv.innerHTML = '<div class="bot-message"><strong>RegCap GPT:</strong> I\'m sorry, but I need access to documents to answer your question. Please upload a PDF document first.</div>';
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }, 2000);
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
                        
                        // Show success message (simulated)
                        setTimeout(function() {
                            var successMsg = document.createElement('div');
                            successMsg.className = 'alert alert-success mt-2';
                            successMsg.innerHTML = '<i class="fa fa-check-circle"></i> File uploaded successfully!';
                            uploadForm.appendChild(successMsg);
                            
                            // Update document list
                            var documentList = document.getElementById('documentList');
                            documentList.innerHTML = '';
                            
                            for (var i = 0; i < fileInput.files.length; i++) {
                                var docItem = document.createElement('div');
                                docItem.className = 'document-item';
                                docItem.innerHTML = '<i class="fas fa-file-pdf document-icon"></i> ' + fileInput.files[i].name;
                                documentList.appendChild(docItem);
                            }
                            
                            // Reset button
                            uploadBtn.innerHTML = originalBtnText;
                            uploadBtn.disabled = false;
                        }, 1500);
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
                        // Simulated session creation
                        alert('New session created successfully!');
                    }
                });
            }
        });
    </script>
</body>
</html>
    """

if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='RegCap GPT Minimal UI Fix')
    parser.add_argument('--port', type=int, default=5003, help='Port to run the server on')
    args = parser.parse_args()
    
    # Use HTTPS in production
    app.run(host='0.0.0.0', port=args.port)