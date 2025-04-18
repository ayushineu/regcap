"""
RegCap GPT - Deployment Version

This is a streamlined version of the RegCap GPT application specifically for deployment,
with all the core functionality but optimized for reliable deployment.
"""

import os
import time
import json
import uuid
import threading
import pickle
import base64
import sys
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import openai
import PyPDF2

app = Flask(__name__)
app.secret_key = "regcap_secure_key"

# Define data storage paths
STORAGE_FOLDER = 'data_storage'
if not os.path.exists(STORAGE_FOLDER):
    os.makedirs(STORAGE_FOLDER)

# Define upload folder
UPLOAD_FOLDER = 'data_storage'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Dictionary to store processing status for each question
processing_status = {}

# Core functions
def get_current_session():
    """Get or create the current session ID."""
    if 'current_session' not in session:
        session['current_session'] = str(uuid.uuid4())
    return session['current_session']

def create_new_session():
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    session['current_session'] = session_id
    
    # Create session directory if it doesn't exist
    session_dir = os.path.join(STORAGE_FOLDER, session_id)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        
    return session_id

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n\n"
    
    # Split into chunks (simple approach)
    chunks = []
    words = text.split()
    chunk_size = 300  # words per chunk
    
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

def save_document_chunks(document_name, chunks, session_id=None):
    """Save document chunks to storage."""
    if session_id is None:
        session_id = get_current_session()
    
    session_dir = os.path.join(STORAGE_FOLDER, session_id)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
    # Create documents directory if it doesn't exist
    docs_dir = os.path.join(session_dir, 'documents')
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
    
    # Create a pickle file for this document
    doc_path = os.path.join(docs_dir, f"{secure_filename(document_name)}.pickle")
    
    with open(doc_path, 'wb') as f:
        pickle.dump(chunks, f)

def get_document_chunks(session_id=None):
    """Get document chunks for the given session."""
    if session_id is None:
        session_id = get_current_session()
    
    session_dir = os.path.join(STORAGE_FOLDER, session_id)
    docs_dir = os.path.join(session_dir, 'documents')
    
    if not os.path.exists(docs_dir):
        return {}
    
    chunks = {}
    for filename in os.listdir(docs_dir):
        if filename.endswith('.pickle'):
            doc_path = os.path.join(docs_dir, filename)
            doc_name = filename[:-7]  # Remove .pickle
            
            try:
                with open(doc_path, 'rb') as f:
                    doc_chunks = pickle.load(f)
                chunks[doc_name] = doc_chunks
            except Exception as e:
                print(f"Error loading document {doc_name}: {e}")
    
    return chunks

def save_chat_history(question, answer, session_id=None):
    """Save a question-answer pair to chat history."""
    if session_id is None:
        session_id = get_current_session()
    
    session_dir = os.path.join(STORAGE_FOLDER, session_id)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
    # Create history directory if it doesn't exist
    history_dir = os.path.join(session_dir, 'history')
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
    
    # Save with timestamp
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    history_item = {
        'question': question,
        'answer': answer,
        'timestamp': timestamp
    }
    
    history_path = os.path.join(history_dir, f"{int(time.time())}.pickle")
    with open(history_path, 'wb') as f:
        pickle.dump(history_item, f)
    
    print(f"Saved chat history with timestamp: {timestamp}")

def get_chat_history(session_id=None):
    """Get chat history for the given session."""
    if session_id is None:
        session_id = get_current_session()
    
    session_dir = os.path.join(STORAGE_FOLDER, session_id)
    history_dir = os.path.join(session_dir, 'history')
    
    if not os.path.exists(history_dir):
        return []
    
    history = []
    for filename in sorted(os.listdir(history_dir)):
        if filename.endswith('.pickle'):
            try:
                with open(os.path.join(history_dir, filename), 'rb') as f:
                    item = pickle.load(f)
                history.append((item['question'], item['answer']))
            except Exception as e:
                print(f"Error loading history item {filename}: {e}")
    
    return history

def list_all_sessions():
    """List all available sessions."""
    if not os.path.exists(STORAGE_FOLDER):
        return {}
    
    sessions = {}
    for dirname in os.listdir(STORAGE_FOLDER):
        if os.path.isdir(os.path.join(STORAGE_FOLDER, dirname)):
            # Use the directory creation time as the timestamp
            try:
                dir_stat = os.stat(os.path.join(STORAGE_FOLDER, dirname))
                sessions[dirname] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dir_stat.st_ctime))
            except:
                sessions[dirname] = "Unknown"
    
    return sessions

def generate_answer(question, context_chunks):
    """Simple answer generation for deployment purposes."""
    try:
        # Format the context
        context_text = ""
        for chunk in context_chunks[:5]:  # Limit to first 5 chunks
            if isinstance(chunk, dict) and "content" in chunk:
                context_text += chunk["content"] + "\n\n"
            else:
                context_text += str(chunk) + "\n\n"
        
        prompt = f"""
        You are RegCap GPT, a regulatory document analysis assistant. Use ONLY the following information to answer the question.
        Do not use any information not provided here.
        
        INFORMATION:
        {context_text}
        
        QUESTION:
        {question}
        
        ANSWER:
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are RegCap GPT, a regulatory document analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3,
        )
        
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print(f"Error generating answer: {str(e)}")
        return f"I'm sorry, but I encountered an error when trying to generate an answer: {str(e)}"

def update_question_status(question_id, stage=None, progress=None, done=None, error=None, answer=None, has_diagram=None, diagram_code=None):
    """Update the status of a question being processed in the background."""
    global processing_status
    
    if question_id not in processing_status:
        processing_status[question_id] = {}
    
    if stage is not None:
        processing_status[question_id]['stage'] = stage
    
    if progress is not None:
        processing_status[question_id]['progress'] = progress
    
    if done is not None:
        processing_status[question_id]['done'] = done
    
    if error is not None:
        processing_status[question_id]['error'] = error
    
    if answer is not None:
        processing_status[question_id]['answer'] = answer
    
    if has_diagram is not None:
        processing_status[question_id]['has_diagram'] = has_diagram
    
    if diagram_code is not None:
        processing_status[question_id]['diagram_code'] = diagram_code

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
        
        # Update status: Generating answer
        update_question_status(question_id, stage="Generating answer", progress=50)
        
        # Generate the answer
        answer = generate_answer(question, all_chunks)
        
        # Save to chat history
        save_chat_history(question, answer, session_id)
        
        # Update status: Complete
        update_question_status(
            question_id,
            stage="Complete",
            progress=100,
            done=True,
            answer=answer,
            has_diagram=False
        )
        
        print(f"Question {question_id}: Processing complete")
    except Exception as e:
        print(f"Error processing question: {str(e)}")
        update_question_status(
            question_id,
            stage="Error",
            progress=100,
            done=True,
            error=str(e)
        )

# Routes
@app.route('/')
def index():
    """Render the main application page."""
    session_id = get_current_session()
    
    # Get data for the current session
    documents = get_document_chunks(session_id)
    chat_history = get_chat_history(session_id)
    
    # List all available sessions
    sessions = list_all_sessions()
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RegCap GPT - Regulatory Document Analysis</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    
    <style>
        :root {
            --primary-color: #0088cc;
            --primary-dark: #006699;
            --secondary-color: #5bc0de;
            --primary-bg: #ffffff;
            --secondary-bg: #f8f9fa;
            --tertiary-bg: #e9ecef;
            --primary-text: #212529;
            --secondary-text: #6c757d;
            --border-color: #dee2e6;
            --border-radius: 0.375rem;
            --light-text: #ffffff;
        }
        
        [data-theme="dark"] {
            --primary-color: #0099e6;
            --primary-dark: #0077b3;
            --secondary-color: #5bc0de;
            --primary-bg: #212529;
            --secondary-bg: #343a40;
            --tertiary-bg: #495057;
            --primary-text: #f8f9fa;
            --secondary-text: #adb5bd;
            --border-color: #495057;
            --light-text: #ffffff;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--secondary-bg);
            color: var(--primary-text);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            margin: 0;
            padding: 0;
        }
        
        /* Beta banner */
        .beta-banner {
            background-color: rgba(0, 136, 204, 0.1);
            border-bottom: 1px solid rgba(0, 136, 204, 0.2);
            padding: 0.5rem 2rem;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .beta-banner-content {
            font-size: 0.9rem;
            color: #006699;
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
        
        /* Main container */
        .main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        /* Navigation sidebar */
        .nav-sidebar {
            width: 260px;
            background-color: var(--primary-bg);
            border-right: 1px solid var(--border-color);
            padding: 1.5rem 0;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        
        .app-logo {
            padding: 0 1.5rem 1.5rem;
            text-align: center;
        }
        
        .app-logo img {
            max-width: 160px;
            height: auto;
        }
        
        .app-name {
            color: var(--primary-text);
            font-weight: 700;
            font-size: 1.25rem;
            margin: 0.5rem 0 0;
        }
        
        .app-tagline {
            color: var(--secondary-text);
            font-size: 0.875rem;
            margin: 0.25rem 0 0;
        }
        
        .nav-item {
            padding: 0.75rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--secondary-text);
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 500;
        }
        
        .nav-item:hover, .nav-item.active {
            background-color: rgba(0, 136, 204, 0.1);
            color: var(--primary-color);
        }
        
        .nav-item.active {
            border-left: 3px solid var(--primary-color);
            padding-left: calc(1.5rem - 3px);
        }
        
        .nav-section-title {
            padding: 1.5rem 1.5rem 0.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--secondary-text);
            font-weight: 600;
        }
        
        /* Content area */
        .content-wrapper {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .panel-title {
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--border-color);
            font-weight: 600;
            background-color: var(--primary-bg);
        }
        
        .content-area {
            flex: 1;
            padding: 2rem;
            overflow-y: auto;
            background-color: var(--secondary-bg);
        }
        
        /* Chat container */
        .chat-container {
            background-color: var(--primary-bg);
            border-radius: var(--border-radius);
            border: 1px solid var(--border-color);
            height: 70vh;
            overflow-y: auto;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .user-message, .bot-message {
            margin-bottom: 1rem;
            padding: 1rem;
            border-radius: var(--border-radius);
            max-width: 80%;
        }
        
        .user-message {
            background-color: var(--tertiary-bg);
            margin-left: auto;
            align-self: flex-end;
        }
        
        .bot-message {
            background-color: var(--secondary-bg);
            margin-right: auto;
            align-self: flex-start;
        }
        
        .diagram-message {
            width: 100%;
            max-width: 100%;
        }
        
        /* Content panels */
        .content-panel {
            display: none;
        }
        
        .content-panel.active {
            display: block;
        }
        
        /* Mermaid diagrams */
        .diagram-container {
            background-color: var(--primary-bg);
            border-radius: var(--border-radius);
            padding: 1rem;
            border: 1px solid var(--border-color);
            overflow: auto;
        }
        
        .mermaid-container {
            padding: 1rem;
            background-color: var(--primary-bg);
            border-radius: var(--border-radius);
            max-width: 100%;
            overflow: auto;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 992px) {
            .main-container {
                flex-direction: column;
            }
            
            .nav-sidebar {
                width: 100%;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
                padding: 1rem 0;
            }
            
            .app-logo {
                padding: 0 1rem 1rem;
            }
            
            .nav-item {
                padding: 0.5rem 1rem;
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
        }
        
        .feature-list-item {
            margin-bottom: 0.5rem;
            padding-left: 1.5rem;
            position: relative;
        }
        
        .feature-list-item::before {
            content: "•";
            position: absolute;
            left: 0.5rem;
            color: var(--primary-color);
        }
    </style>
</head>
<body>
    <!-- Beta Banner -->
    <div class="beta-banner" id="betaBanner">
        <div class="beta-banner-content">
            <strong>🚧 Beta Notice:</strong> RegCap GPT is currently in active development. Some features may be limited or evolving.
        </div>
        <button class="beta-close-btn" id="closeBetaBanner">&times;</button>
    </div>
    
    <div class="main-container">
        <!-- Navigation Sidebar -->
        <div class="nav-sidebar">
            <div class="app-logo">
                <h1 class="app-name">RegCap GPT</h1>
                <p class="app-tagline">Regulatory Intelligence</p>
            </div>
            
            <div class="nav-section-title">Navigation</div>
            
            <div class="nav-item active" data-panel="chat-panel">
                <i class="fa fa-comments"></i> Chat
            </div>
            
            <div class="nav-item" data-panel="docs-panel">
                <i class="fa fa-file-pdf-o"></i> Documents
            </div>
            
            <div class="nav-item" data-panel="sessions-panel">
                <i class="fa fa-database"></i> Sessions
            </div>
            
            <div class="nav-section-title">Settings</div>
            
            <div class="nav-item" id="featureToggle">
                <i class="fa fa-star"></i> Features
                <i class="fa fa-angle-down toggle-icon" style="margin-left: auto;"></i>
            </div>
            
            <div id="featureList" class="feature-list" style="display: none;">
                <div class="feature-list-date">Last Updated: April 18, 2025</div>
                <div class="feature-list-item">Upload and process PDF documents</div>
                <div class="feature-list-item">Ask questions about regulatory content</div>
                <div class="feature-list-item">Visualize regulatory processes with diagrams</div>
                <div class="feature-list-item">Multiple session support</div>
                <div class="feature-list-item">Dark/light theme toggle</div>
            </div>
            
            <div class="theme-toggle" id="themeToggle">
                <i class="fa fa-moon-o"></i> Dark Mode
            </div>
        </div>
        
        <!-- Content Area -->
        <div class="content-wrapper">
            <div class="panel-title" id="currentPanelTitle">
                <i class="fa fa-comments"></i> Chat with your Documents
            </div>
            
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
                                    <i class="fa fa-upload"></i> Upload Documents
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
                                <ul class="list-group">
                                    {% for doc_name in documents.keys() %}
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            <div>
                                                <i class="fa fa-file-pdf-o text-danger"></i>
                                                {{ doc_name }}
                                            </div>
                                            <span class="badge bg-primary rounded-pill">
                                                {{ documents[doc_name]|length }} chunks
                                            </span>
                                        </li>
                                    {% endfor %}
                                </ul>
                            {% else %}
                                <div class="text-center text-muted my-3">
                                    <i class="fa fa-folder-open-o fa-2x mb-3"></i>
                                    <p>No documents uploaded yet.</p>
                                </div>
                            {% endif %}
                        </div>
                    </div>
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
            console.log("DOM loaded");
            
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
                    
                    // Add active class to the clicked navigation item
                    this.classList.add('active');
                });
            }
            
            // Beta banner close button
            var betaBanner = document.getElementById('betaBanner');
            var closeBetaBanner = document.getElementById('closeBetaBanner');
            
            if (betaBanner && closeBetaBanner) {
                closeBetaBanner.addEventListener('click', function() {
                    betaBanner.style.display = 'none';
                    // Store the banner state in localStorage
                    localStorage.setItem('betaBannerClosed', 'true');
                });
                
                // Check if banner was previously closed
                if (localStorage.getItem('betaBannerClosed') === 'true') {
                    betaBanner.style.display = 'none';
                }
            }
            
            // Theme toggling
            function setupThemeToggle() {
                var themeToggle = document.getElementById('themeToggle');
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
                        
                        // Clear "No chat history" message if it exists
                        if (chatMessages.querySelector('.text-center.text-muted')) {
                            chatMessages.innerHTML = ''; // Clear the "No chat history" message
                        }
                        
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
                                // Show success message in UI instead of alert
                                var successMsg = document.createElement('div');
                                successMsg.className = 'alert alert-success mt-2';
                                successMsg.innerHTML = '<i class="fa fa-check-circle"></i> Files successfully processed: ' + data.message;
                                uploadForm.appendChild(successMsg);
                                
                                // Reload page after a short delay to refresh the documents list
                                setTimeout(function() {
                                    window.location.reload();
                                }, 1500);
                            } else {
                                // Show error in UI instead of alert
                                var errorMsg = document.createElement('div');
                                errorMsg.className = 'alert alert-danger mt-2';
                                errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> Error: ' + data.error;
                                uploadForm.appendChild(errorMsg);
                                
                                // Reset button
                                uploadBtn.innerHTML = originalBtnText;
                                uploadBtn.disabled = false;
                            }
                        })
                        .catch(error => {
                            console.error('Error uploading files:', error);
                            // Show error in UI
                            var errorMsg = document.createElement('div');
                            errorMsg.className = 'alert alert-danger mt-2';
                            errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> An error occurred while uploading the files.';
                            uploadForm.appendChild(errorMsg);
                            
                            // Reset button
                            uploadBtn.innerHTML = originalBtnText;
                            uploadBtn.disabled = false;
                        });
                    } else {
                        // Show error in UI
                        var errorMsg = document.createElement('div');
                        errorMsg.className = 'alert alert-danger mt-2';
                        errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> Please select at least one file to upload.';
                        uploadForm.appendChild(errorMsg);
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
                                // Show success message in UI
                                var successMsg = document.createElement('div');
                                successMsg.className = 'alert alert-success mt-2';
                                successMsg.innerHTML = '<i class="fa fa-check-circle"></i> New session created successfully!';
                                document.querySelector('.card-body').appendChild(successMsg);
                                
                                // Reload page after a short delay
                                setTimeout(function() {
                                    window.location.reload();
                                }, 1500);
                            } else {
                                // Show error in UI
                                var errorMsg = document.createElement('div');
                                errorMsg.className = 'alert alert-danger mt-2';
                                errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> Error: ' + data.error;
                                document.querySelector('.card-body').appendChild(errorMsg);
                            }
                        })
                        .catch(error => {
                            console.error('Error creating new session:', error);
                            // Show error in UI
                            var errorMsg = document.createElement('div');
                            errorMsg.className = 'alert alert-danger mt-2';
                            errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> An error occurred while creating a new session.';
                            document.querySelector('.card-body').appendChild(errorMsg);
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
                                // Show success message in UI
                                var successMsg = document.createElement('div');
                                successMsg.className = 'alert alert-success mt-2';
                                successMsg.innerHTML = '<i class="fa fa-check-circle"></i> Switched to session ' + sessionId;
                                document.querySelector('.card-body').appendChild(successMsg);
                                
                                // Reload page after a short delay
                                setTimeout(function() {
                                    window.location.reload();
                                }, 1500);
                            } else {
                                // Show error in UI
                                var errorMsg = document.createElement('div');
                                errorMsg.className = 'alert alert-danger mt-2';
                                errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> Error: ' + data.error;
                                document.querySelector('.card-body').appendChild(errorMsg);
                            }
                        })
                        .catch(error => {
                            console.error('Error switching sessions:', error);
                            // Show error in UI
                            var errorMsg = document.createElement('div');
                            errorMsg.className = 'alert alert-danger mt-2';
                            errorMsg.innerHTML = '<i class="fa fa-exclamation-circle"></i> An error occurred while switching sessions.';
                            document.querySelector('.card-body').appendChild(errorMsg);
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

@app.route('/question-status/<question_id>', methods=['GET'])
def get_question_status(question_id):
    """Get the status of a specific question."""
    global processing_status
    
    if question_id in processing_status:
        return jsonify(processing_status[question_id])
    else:
        return jsonify({
            'error': 'Question ID not found',
            'done': True
        })

if __name__ == "__main__":
    # Get port from command line
    port = 8080 # Default port
    if len(sys.argv) > 1 and '--port' in sys.argv[1]:
        port = int(sys.argv[1].split('=')[1])
    
    print("Starting RegCap GPT in deployment mode on port:", port)
    app.run(host="0.0.0.0", port=port)