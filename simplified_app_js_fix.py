"""
RegCap GPT - Simplified Version with Fixed JavaScript

A streamlined version of the RegCap GPT application with minimal
JavaScript and only essential functionality to ensure everything works correctly.
"""

from flask import Flask, render_template_string, request, session, jsonify
import os
import uuid
import threading
import time

app = Flask(__name__)
app.secret_key = "regcap-secret-key-2024"

# Simple in-memory storage
session_store = {}
document_store = {}
chat_history_store = {}
question_status_store = {}

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

def update_question_status(question_id, stage=None, progress=None, done=None, error=None, answer=None):
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
    <title>RegCap GPT (Simplified)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
            font-family: Arial, sans-serif;
        }
        .container {
            max-width: 1200px;
        }
        .tab-nav {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab-button {
            padding: 10px 15px;
            background-color: #f0f0f0;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .tab-button.active {
            background-color: #0088cc;
            color: white;
        }
        .tab-content {
            display: none;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .tab-content.active {
            display: block;
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 15px;
            background-color: white;
        }
        .user-message, .bot-message {
            padding: 10px 15px;
            margin: 10px 0;
            border-radius: 10px;
            max-width: 80%;
        }
        .user-message {
            background-color: #0088cc;
            color: white;
            margin-left: auto;
        }
        .bot-message {
            background-color: #e9ecef;
            margin-right: auto;
        }
        .theme-button {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 8px 12px;
            background-color: #343a40;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">RegCap GPT <small class="text-muted">Simplified Version</small></h1>
        
        <button id="themeToggle" class="theme-button">
            <span id="themeText">Dark Mode</span>
        </button>
        
        <div class="tab-nav">
            <button class="tab-button active" data-tab="chat-tab">Chat</button>
            <button class="tab-button" data-tab="docs-tab">Documents</button>
            <button class="tab-button" data-tab="sessions-tab">Sessions</button>
        </div>
        
        <div id="chat-tab" class="tab-content active">
            <h2>Chat with your Documents</h2>
            
            <div id="chatContainer" class="chat-container">
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
                        <p>No chat history yet. Upload documents and start asking questions!</p>
                    </div>
                {% endif %}
            </div>
            
            <form id="questionForm" class="mb-4">
                <div class="input-group">
                    <input type="text" id="questionInput" class="form-control" 
                        placeholder="Ask a question about your documents..." required>
                    <button class="btn btn-primary" type="submit">Send</button>
                </div>
            </form>
        </div>
        
        <div id="docs-tab" class="tab-content">
            <h2>Document Management</h2>
            
            <form id="uploadForm" class="mb-4" enctype="multipart/form-data">
                <div class="mb-3">
                    <label for="documentUpload" class="form-label">Upload PDF Documents</label>
                    <input class="form-control" type="file" id="documentUpload" name="files" multiple accept=".pdf">
                </div>
                <button type="submit" class="btn btn-primary">Upload</button>
            </form>
            
            <div class="card">
                <div class="card-header">Uploaded Documents</div>
                <div class="card-body">
                    {% if documents %}
                        <ul class="list-group">
                            {% for doc in documents %}
                                <li class="list-group-item">{{ doc.name }}</li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p class="text-muted">No documents uploaded yet.</p>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div id="sessions-tab" class="tab-content">
            <h2>Session Management</h2>
            
            <div class="card mb-4">
                <div class="card-header">Current Session</div>
                <div class="card-body">
                    <p>Current Session ID: <strong>{{ session_id }}</strong></p>
                    <button id="newSessionBtn" class="btn btn-primary">Create New Session</button>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">Available Sessions</div>
                <div class="card-body">
                    {% if sessions %}
                        <div class="list-group">
                            {% for session_id in sessions %}
                                <button class="list-group-item list-group-item-action session-switch-btn" 
                                    data-session-id="{{ session_id }}">
                                    Switch to Session {{ session_id }}
                                </button>
                            {% endfor %}
                        </div>
                    {% else %}
                        <p class="text-muted">No other sessions available.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded');
            
            // Tab navigation
            const tabButtons = document.querySelectorAll('.tab-button');
            const tabContents = document.querySelectorAll('.tab-content');
            
            tabButtons.forEach(button => {
                button.addEventListener('click', function() {
                    console.log('Tab clicked: ' + this.getAttribute('data-tab'));
                    const tabId = this.getAttribute('data-tab');
                    
                    tabContents.forEach(content => {
                        content.classList.remove('active');
                    });
                    
                    tabButtons.forEach(btn => {
                        btn.classList.remove('active');
                    });
                    
                    document.getElementById(tabId).classList.add('active');
                    this.classList.add('active');
                });
            });
            
            // Theme toggle
            const themeToggle = document.getElementById('themeToggle');
            const themeText = document.getElementById('themeText');
            let darkMode = false;
            
            themeToggle.addEventListener('click', function() {
                console.log('Theme toggle clicked');
                darkMode = !darkMode;
                
                if (darkMode) {
                    document.body.style.backgroundColor = '#121212';
                    document.body.style.color = '#f0f0f0';
                    themeText.textContent = 'Light Mode';
                } else {
                    document.body.style.backgroundColor = '';
                    document.body.style.color = '';
                    themeText.textContent = 'Dark Mode';
                }
            });
            
            // Question form
            const questionForm = document.getElementById('questionForm');
            const questionInput = document.getElementById('questionInput');
            const chatContainer = document.getElementById('chatContainer');
            
            questionForm.addEventListener('submit', function(e) {
                e.preventDefault();
                console.log('Question submitted');
                
                const question = questionInput.value.trim();
                if (!question) return;
                
                // Add user message to chat
                const userDiv = document.createElement('div');
                userDiv.className = 'user-message';
                userDiv.innerHTML = '<strong>You:</strong> ' + question;
                chatContainer.appendChild(userDiv);
                
                // Add temporary processing message
                const processingDiv = document.createElement('div');
                processingDiv.className = 'bot-message';
                processingDiv.innerHTML = '<strong>RegCap GPT:</strong> Processing your question...';
                chatContainer.appendChild(processingDiv);
                
                // Clear input and scroll to bottom
                questionInput.value = '';
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                // Send question to server
                fetch('/ask-question', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ question: question })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Received response:', data);
                    
                    if (data.success) {
                        const questionId = data.question_id;
                        
                        // Poll for status updates
                        const pollInterval = setInterval(function() {
                            fetch('/question-status/' + questionId)
                                .then(response => response.json())
                                .then(status => {
                                    if (status.done) {
                                        clearInterval(pollInterval);
                                        
                                        if (status.error) {
                                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span style="color: red;">Error: ' + 
                                                status.error + '</span>';
                                        } else {
                                            processingDiv.innerHTML = '<strong>RegCap GPT:</strong> ' + status.answer;
                                        }
                                        
                                        chatContainer.scrollTop = chatContainer.scrollHeight;
                                    }
                                })
                                .catch(error => {
                                    console.error('Error checking status:', error);
                                    clearInterval(pollInterval);
                                    processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span style="color: red;">' + 
                                        'Error checking question status. Please try again.</span>';
                                });
                        }, 1000);
                    } else {
                        processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span style="color: red;">' + 
                            'Error: ' + (data.error || 'Failed to process question') + '</span>';
                    }
                })
                .catch(error => {
                    console.error('Error submitting question:', error);
                    processingDiv.innerHTML = '<strong>RegCap GPT:</strong> <span style="color: red;">' + 
                        'Error submitting question. Please try again.</span>';
                });
            });
            
            // Document upload
            const uploadForm = document.getElementById('uploadForm');
            
            uploadForm.addEventListener('submit', function(e) {
                e.preventDefault();
                console.log('Upload form submitted');
                
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
                submitBtn.innerHTML = 'Uploading...';
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
                    alert('Error uploading files. Please try again.');
                    submitBtn.innerHTML = originalBtnText;
                    submitBtn.disabled = false;
                });
            });
            
            // New session
            const newSessionBtn = document.getElementById('newSessionBtn');
            
            newSessionBtn.addEventListener('click', function() {
                console.log('New session button clicked');
                
                if (confirm('Create a new session? This will start with a clean slate.')) {
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
                            alert('Error: ' + (data.error || 'Failed to create new session'));
                        }
                    })
                    .catch(error => {
                        console.error('Error creating new session:', error);
                        alert('Error creating new session. Please try again.');
                    });
                }
            });
            
            // Session switch
            const sessionSwitchBtns = document.querySelectorAll('.session-switch-btn');
            
            sessionSwitchBtns.forEach(button => {
                button.addEventListener('click', function() {
                    const sessionId = this.getAttribute('data-session-id');
                    console.log('Switch to session: ' + sessionId);
                    
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
                            alert('Error switching session. Please try again.');
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
            # In a real app, we'd process the PDF content here
            # For this simplified version, just store the filename
            document_store[session_id].append({
                'name': file.filename,
                'content': 'Sample content for ' + file.filename
            })
    
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
        # Simulate processing stages
        update_question_status(question_id, stage="Analyzing question", progress=20, done=False)
        time.sleep(1)
        
        update_question_status(question_id, stage="Searching for information", progress=50, done=False)
        time.sleep(1.5)
        
        update_question_status(question_id, stage="Generating answer", progress=80, done=False)
        time.sleep(1)
        
        # Generate a sample answer
        answer = f"This is a sample answer to your question: '{question}'. In a real app, this would be generated based on your documents."
        
        # Update status as complete
        update_question_status(
            question_id,
            stage="Complete",
            progress=100,
            done=True,
            answer=answer
        )
        
        # Save to chat history
        session_id = get_current_session()
        if session_id not in chat_history_store:
            chat_history_store[session_id] = []
        
        chat_history_store[session_id].append((question, answer))
        
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
    app.run(host='0.0.0.0', port=5003)