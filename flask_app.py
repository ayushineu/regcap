from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import os
import base64
import pickle
import json
import time
import tempfile
from werkzeug.utils import secure_filename
import PyPDF2
from openai import OpenAI
import numpy as np
import faiss

# Initialize OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

app = Flask(__name__)

# Ensure storage directories exist
os.makedirs("data_storage", exist_ok=True)
os.makedirs("data_storage/uploads", exist_ok=True)

# Simple file-based storage system
class SimpleStorage:
    def __init__(self):
        self.storage_path = "data_storage/data.json"
        self.data = self._load_data()
        
    def _load_data(self):
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading data: {e}")
            return {}
        
    def _save_data(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.data, f)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False
        
    def __getitem__(self, key):
        return self.data.get(key)
        
    def __setitem__(self, key, value):
        self.data[key] = value
        self._save_data()
        
    def __contains__(self, key):
        return key in self.data

# Initialize storage
storage = SimpleStorage()

# Session management
def get_current_session():
    """Get or create the current session ID."""
    if "current_session" not in storage:
        session_id = create_new_session()
        return session_id
    return storage["current_session"]

def create_new_session():
    """Create a new session and return its ID."""
    session_id = f"session_{int(time.time())}"
    storage["current_session"] = session_id
    
    # Initialize session data
    if "sessions" not in storage:
        storage["sessions"] = {}
        
    storage["sessions"][session_id] = {
        "created_at": time.time(),
        "documents": {},
        "chat_history": [],
        "diagrams": []
    }
    
    return session_id

# Utility functions
def encode_for_storage(obj):
    """Encode complex objects for storage."""
    try:
        pickled = pickle.dumps(obj)
        encoded = base64.b64encode(pickled).decode('utf-8')
        return encoded
    except Exception as e:
        print(f"Error encoding object: {e}")
        return None

def decode_from_storage(encoded_obj):
    """Decode complex objects from storage."""
    try:
        decoded_bytes = base64.b64decode(encoded_obj.encode('utf-8'))
        unpickled = pickle.loads(decoded_bytes)
        return unpickled
    except Exception as e:
        print(f"Error decoding object: {e}")
        return None

# Document processing
def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        text_chunks = []
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text = page.extract_text()
                
                if text and text.strip():
                    text_chunks.append({
                        "content": text,
                        "metadata": {
                            "page": page_num + 1,
                            "source": os.path.basename(file_path)
                        }
                    })
                
        return text_chunks
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return []

def save_document_chunks(document_name, text_chunks):
    """Save document chunks to storage."""
    session_id = get_current_session()
    
    try:
        if "sessions" not in storage:
            storage["sessions"] = {}
            
        if session_id not in storage["sessions"]:
            storage["sessions"][session_id] = {
                "created_at": time.time(),
                "documents": {},
                "chat_history": [],
                "diagrams": []
            }
            
        storage["sessions"][session_id]["documents"][document_name] = encode_for_storage(text_chunks)
        return True
    except Exception as e:
        print(f"Error saving document chunks: {e}")
        return False

def get_document_chunks(session_id=None):
    """Get all document chunks for a session."""
    if session_id is None:
        session_id = get_current_session()
        
    try:
        if "sessions" not in storage or session_id not in storage["sessions"]:
            return {}
            
        documents = storage["sessions"][session_id]["documents"]
        result = {}
        
        for doc_name, encoded_chunks in documents.items():
            decoded_chunks = decode_from_storage(encoded_chunks)
            if decoded_chunks is not None:
                result[doc_name] = decoded_chunks
                
        return result
    except Exception as e:
        print(f"Error getting document chunks: {e}")
        return {}

def get_all_document_chunks(session_id=None):
    """Get a flat list of all document chunks."""
    documents = get_document_chunks(session_id)
    all_chunks = []
    
    for doc_name, chunks in documents.items():
        all_chunks.extend(chunks)
        
    return all_chunks

# Vector store functions
def get_embedding(text):
    """Get embedding for text using OpenAI."""
    try:
        text = text.replace("\n", " ")
        max_retries = 5
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
                return np.array(response.data[0].embedding, dtype=np.float32)
            except Exception as e:
                if "rate_limit_exceeded" in str(e) and attempt < max_retries - 1:
                    print(f"Rate limit exceeded, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        
        # If we get here, all retries failed
        return None
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def create_vector_store(chunks):
    """Create a FAISS vector store from chunks."""
    if not chunks:
        return None
        
    try:
        # Get embeddings for chunks
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i+batch_size]
            batch_embeddings = [get_embedding(text) for text in batch]
            
            # Skip any None values (failed embeddings)
            batch_embeddings = [emb for emb in batch_embeddings if emb is not None]
            embeddings.extend(batch_embeddings)
            
            # Add a sleep to avoid rate limiting
            time.sleep(0.5)
        
        # Make sure we have at least one embedding
        if not embeddings:
            print("No valid embeddings were generated.")
            return None
            
        # Create FAISS index
        dimension = len(embeddings[0])
        index = faiss.IndexFlatL2(dimension)
        
        # Make sure all embeddings have the same shape
        filtered_embeddings = []
        filtered_chunks = []
        
        for i, embedding in enumerate(embeddings):
            if len(embedding) == dimension:
                filtered_embeddings.append(embedding)
                if i < len(chunks):
                    filtered_chunks.append(chunks[i])
        
        # Make sure we have at least one valid embedding after filtering
        if not filtered_embeddings:
            print("No consistent embeddings were found.")
            return None
            
        embeddings_array = np.array(filtered_embeddings).astype('float32')
        index.add(embeddings_array)
        
        return {
            "index": index,
            "chunks": filtered_chunks,
            "embeddings": embeddings_array
        }
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None

def get_similar_chunks(query, vector_store, top_k=5):
    """Find chunks similar to query in vector store."""
    if not vector_store:
        return []
        
    try:
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return []
            
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search for similar chunks
        distances, indices = vector_store["index"].search(query_embedding, top_k)
        
        # Get the chunks
        similar_chunks = [vector_store["chunks"][idx] for idx in indices[0]]
        return similar_chunks
    except Exception as e:
        print(f"Error getting similar chunks: {e}")
        return []

# OpenAI helper functions
def generate_answer(question, context_chunks, max_retries=3):
    """Generate answer using OpenAI with retry mechanism."""
    import time
    
    if not context_chunks:
        return "I don't have enough information to answer this question. Please upload relevant documents."
        
    # Prepare context
    context = "\n\n".join([chunk["content"] for chunk in context_chunks])
    
    # Construct the prompt
    messages = [
        {"role": "system", "content": "You are an AI assistant specialized in regulatory document analysis. "
                                     "Answer questions based ONLY on the provided context. "
                                     "If you don't know the answer based on the context, say so clearly."},
        {"role": "user", "content": f"Context information: {context}\n\nQuestion: {question}"}
    ]
    
    # Retry logic with exponential backoff
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            print(f"Attempt {retry_count + 1} to generate answer for: {question[:100]}...")
            
            # Generate response with a timeout
            response = client.chat.completions.create(
                model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=messages,
                max_tokens=1000,
                timeout=45  # 45 second timeout
            )
            
            answer = response.choices[0].message.content
            print(f"Successfully generated answer on attempt {retry_count + 1}")
            return answer
            
        except Exception as e:
            retry_count += 1
            last_error = e
            print(f"Error on attempt {retry_count}: {e}")
            
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    # If all retries fail
    print(f"Failed after {max_retries} attempts. Last error: {last_error}")
    return "Sorry, I was unable to generate an answer at this time. Please try asking a more specific question or try again later."

def generate_diagram(question, context_chunks, diagram_type="flowchart"):
    """Generate a Mermaid diagram based on context."""
    try:
        print(f"Starting diagram generation for {diagram_type}...")
        
        if not context_chunks:
            print("No context chunks available for diagram generation")
            return False, "I don't have enough information to generate a diagram. Please upload relevant documents."
            
        # Prepare context
        context = "\n\n".join([chunk["content"] for chunk in context_chunks])
        print(f"Prepared context with {len(context)} characters")
        
        # Construct the prompt
        messages = [
            {"role": "system", "content": f"You are an AI assistant specialized in creating {diagram_type} diagrams using Mermaid syntax. "
                                         "Create a diagram based ONLY on the provided context. "
                                         "Return ONLY the Mermaid code without any explanation or markdown formatting."},
            {"role": "user", "content": f"Context information: {context}\n\nCreate a {diagram_type} diagram for: {question}"}
        ]
        
        print("Sending request to OpenAI for diagram generation...")
        # Generate response with retry mechanism
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Generate response with timeout
                response = client.chat.completions.create(
                    model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                    messages=messages,
                    max_tokens=1000,
                    timeout=45  # 45 second timeout
                )
                break  # If successful, break out of retry loop
            except Exception as e:
                if "rate_limit_exceeded" in str(e) and attempt < max_retries - 1:
                    print(f"Rate limit exceeded, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        else:
            # If we exit the loop normally (all retries failed)
            print("All retries failed for diagram generation")
            return False, "Failed to generate diagram after multiple attempts due to API rate limits. Please try again later."
        
        mermaid_code = response.choices[0].message.content.strip()
        print(f"Received mermaid code: {mermaid_code[:100]}...")
        
        # Clean up the response to extract just the Mermaid code
        if "```mermaid" in mermaid_code:
            mermaid_code = mermaid_code.split("```mermaid")[1]
            if "```" in mermaid_code:
                mermaid_code = mermaid_code.split("```")[0].strip()
        elif "```" in mermaid_code:
            parts = mermaid_code.split("```")
            if len(parts) >= 2:
                mermaid_code = parts[1].strip()
                # Check if the first line is the word "mermaid" 
                if mermaid_code.startswith("mermaid\n"):
                    mermaid_code = mermaid_code[8:].strip()
        
        # Ensure proper syntax for the diagram type
        if diagram_type == "flowchart" and not mermaid_code.strip().startswith("flowchart"):
            mermaid_code = "flowchart TD\n" + mermaid_code
        elif diagram_type == "sequence" and not mermaid_code.strip().startswith("sequenceDiagram"):
            mermaid_code = "sequenceDiagram\n" + mermaid_code
        elif diagram_type == "mindmap" and not mermaid_code.strip().startswith("mindmap"):
            mermaid_code = "mindmap\n" + mermaid_code
        
        print("Clean mermaid code extracted, generating explanation...")
        
        # Generate explanation with retry mechanism
        max_retries = 3
        retry_delay = 1.0
        
        # Generate explanation
        explanation_messages = [
            {"role": "system", "content": "You are an AI assistant specialized in explaining diagrams. "
                                         "Provide a clear, concise explanation of the diagram."},
            {"role": "user", "content": f"Diagram: {mermaid_code}\n\nExplain this diagram in simple terms."}
        ]
        
        for attempt in range(max_retries):
            try:
                explanation_response = client.chat.completions.create(
                    model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                    messages=explanation_messages,
                    max_tokens=500,
                    timeout=45  # 45 second timeout
                )
                break  # If successful, break out of retry loop
            except Exception as e:
                if "rate_limit_exceeded" in str(e) and attempt < max_retries - 1:
                    print(f"Rate limit exceeded for explanation, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
        else:
            # If we exit the loop normally (all retries failed)
            print("All retries failed for explanation generation")
            # Still return the diagram even if explanation fails
            explanation = "Explanation could not be generated due to API limitations."
            save_diagram(mermaid_code, explanation, diagram_type)
            return True, (mermaid_code, explanation)
        
        explanation = explanation_response.choices[0].message.content
        print("Explanation generated successfully, saving diagram...")
        
        # Save diagram
        save_diagram(mermaid_code, explanation, diagram_type)
        print("Diagram saved successfully")
        
        return True, (mermaid_code, explanation)
    except Exception as e:
        print(f"Error generating diagram: {str(e)}")
        return False, f"Sorry, I encountered an error while generating a diagram: {str(e)}"

def detect_diagram_request(question):
    """Detect if question is requesting a diagram."""
    try:
        diagram_keywords = ["diagram", "flowchart", "chart", "graph", "visualization", "visualize", "map", "mapping", "sequence", "process flow"]
        question_lower = question.lower()
        
        for keyword in diagram_keywords:
            if keyword in question_lower:
                # Determine diagram type
                if "sequence" in question_lower or "step" in question_lower:
                    return True, "sequence"
                elif "mind map" in question_lower or "concept map" in question_lower:
                    return True, "mindmap"
                else:
                    return True, "flowchart"
                    
        return False, None
    except Exception as e:
        print(f"Error detecting diagram request: {e}")
        return False, None

# Chat history and diagrams
def save_chat_history(question, answer):
    """Save chat history to storage."""
    session_id = get_current_session()
    
    try:
        if "sessions" not in storage:
            storage["sessions"] = {}
            
        if session_id not in storage["sessions"]:
            storage["sessions"][session_id] = {
                "created_at": time.time(),
                "documents": {},
                "chat_history": [],
                "diagrams": []
            }
            
        storage["sessions"][session_id]["chat_history"].append((question, answer))
        return True
    except Exception as e:
        print(f"Error saving chat history: {e}")
        return False

def get_chat_history(session_id=None):
    """Get chat history for a session."""
    if session_id is None:
        session_id = get_current_session()
        
    try:
        if "sessions" not in storage or session_id not in storage["sessions"]:
            return []
            
        return storage["sessions"][session_id]["chat_history"]
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def save_diagram(diagram_code, explanation, diagram_type):
    """Save diagram to storage."""
    session_id = get_current_session()
    
    try:
        if "sessions" not in storage:
            storage["sessions"] = {}
            
        if session_id not in storage["sessions"]:
            storage["sessions"][session_id] = {
                "created_at": time.time(),
                "documents": {},
                "chat_history": [],
                "diagrams": []
            }
            
        storage["sessions"][session_id]["diagrams"].append((diagram_code, explanation, diagram_type))
        return True
    except Exception as e:
        print(f"Error saving diagram: {e}")
        return False

def get_diagrams(session_id=None):
    """Get diagrams for a session."""
    if session_id is None:
        session_id = get_current_session()
        
    try:
        if "sessions" not in storage or session_id not in storage["sessions"]:
            return []
            
        return storage["sessions"][session_id]["diagrams"]
    except Exception as e:
        print(f"Error getting diagrams: {e}")
        return []

# Session management
def list_all_sessions():
    """List all available sessions."""
    try:
        if "sessions" not in storage:
            return {}
            
        sessions = {}
        for session_id, session_data in storage["sessions"].items():
            sessions[session_id] = session_data["created_at"]
            
        return sessions
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return {}

# Flask routes
@app.route('/')
def index():
    """Render the main application page."""
    session_id = get_current_session()
    sessions = list_all_sessions()
    chat_history = get_chat_history()
    diagrams = get_diagrams()
    documents = get_document_chunks()
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Regulatory Document Chatbot</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }
            .chat-container {
                height: 400px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .user-message, .bot-message {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 5px;
            }
            .user-message {
                background-color: #e6f7ff;
                margin-left: 20%;
            }
            .bot-message {
                background-color: #f0f0f0;
                margin-right: 20%;
            }
            .document-section, .diagram-section {
                margin-top: 30px;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .tabs {
                display: flex;
                border-bottom: 1px solid #ddd;
                margin-bottom: 20px;
            }
            .tab {
                padding: 10px 20px;
                cursor: pointer;
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-bottom: none;
                margin-right: 5px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .tab.active {
                background-color: white;
                border-bottom: 1px solid white;
            }
            .tab:hover {
                background-color: #e3e3e3;
            }
            #diagrams-tab-button {
                background-color: #f0f7ff;
                border: 1px solid #c0d5e8;
            }
            #diagrams-tab-button.active {
                background-color: white;
                border-bottom: 1px solid white;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .session-info {
                margin-bottom: 20px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }
            .document-list {
                margin-top: 15px;
            }
            .document-item {
                padding: 5px 0;
            }
            .diagram-item {
                margin-bottom: 30px;
                padding: 15px;
                border: 1px solid #eee;
                border-radius: 5px;
            }
            .diagram-code {
                margin-top: 10px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
                overflow-x: auto;
            }
            .diagram-explanation {
                margin-top: 10px;
                padding: 10px;
                background-color: #e9f7ef;
                border-radius: 5px;
            }
            .diagram-visual {
                margin-top: 20px;
                padding: 10px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .footer {
                margin-top: 50px;
                text-align: center;
                color: #6c757d;
                font-size: 0.9rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mt-4 mb-4">Regulatory Document Chatbot</h1>
            
            <!-- Session Information -->
            <div class="session-info">
                <h5>Current Session: {{ session_id }}</h5>
                <form action="/new_session" method="post" class="mt-2">
                    <button type="submit" class="btn btn-sm btn-primary">Create New Session</button>
                </form>
            </div>
            
            <!-- Tabs -->
            <div class="tabs">
                <div id="chat-tab-button" class="tab active" onclick="openTab(event, 'chat-tab')">Chat</div>
                <div id="documents-tab-button" class="tab" onclick="openTab(event, 'documents-tab')">Documents</div>
                <div id="diagrams-tab-button" class="tab" onclick="openTab(event, 'diagrams-tab')">
                    <span style="position: relative;">
                        Diagrams
                        <div style="position: absolute; top: -8px; right: -8px; background-color: #ff9900; color: white; border-radius: 50%; width: 18px; height: 18px; display: none; font-size: 12px; text-align: center; line-height: 18px;" id="diagrams-notification">!</div>
                    </span>
                </div>
                <div id="sessions-tab-button" class="tab" onclick="openTab(event, 'sessions-tab')">Sessions</div>
            </div>
            
            <!-- Chat Tab -->
            <div id="chat-tab" class="tab-content active">
                <div class="chat-container" id="chat-messages">
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
                            <strong>Bot:</strong> Hello! I'm your regulatory document assistant. Upload documents and ask me questions about them.
                        </div>
                    {% endif %}
                </div>
                
                <form action="/ask" method="post" id="question-form">
                    <div class="mb-3">
                        <label for="question" class="form-label">Your Question:</label>
                        <textarea class="form-control" id="question" name="question" rows="3" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Ask</button>
                </form>
            </div>
            
            <!-- Documents Tab -->
            <div id="documents-tab" class="tab-content">
                <div class="document-section">
                    <h3>Upload Documents</h3>
                    <form action="/upload" method="post" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label for="document" class="form-label">Select PDF Document(s):</label>
                            <input class="form-control" type="file" id="document" name="document" multiple accept=".pdf" required>
                        </div>
                        <button type="submit" class="btn btn-primary">Upload</button>
                    </form>
                    
                    <div class="document-list mt-4">
                        <h4>Uploaded Documents</h4>
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
            </div>
            
            <!-- Diagrams Tab -->
            <div id="diagrams-tab" class="tab-content">
                <div class="diagram-section">
                    <h3>Generated Diagrams</h3>
                    {% if diagrams %}
                        {% for diagram_code, explanation, diagram_type in diagrams %}
                            <div class="diagram-item">
                                <h4>{{ diagram_type|capitalize }} Diagram</h4>
                                <div class="diagram-explanation">
                                    <strong>Explanation:</strong> {{ explanation }}
                                </div>
                                <div class="diagram-visual mt-3 mb-3">
                                    <div class="mermaid">
{{ diagram_code }}
                                    </div>
                                </div>
                                <div class="diagram-actions">
                                    <a href="/view_diagram/{{ loop.index0 }}" class="btn btn-success" target="_blank">
                                        View Diagram in New Tab
                                    </a>
                                </div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p>No diagrams generated yet. Ask a question that requires a diagram or visualization.</p>
                    {% endif %}
                </div>
            </div>
            
            <!-- Sessions Tab -->
            <div id="sessions-tab" class="tab-content">
                <div class="session-section">
                    <h3>Available Sessions</h3>
                    {% if sessions %}
                        <ul class="list-group">
                            {% for s_id, created_at in sessions.items() %}
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    {{ s_id }} 
                                    {% if s_id == session_id %}
                                        <span class="badge bg-primary rounded-pill">Current</span>
                                    {% else %}
                                        <form action="/switch_session" method="post" class="d-inline">
                                            <input type="hidden" name="session_id" value="{{ s_id }}">
                                            <button type="submit" class="btn btn-sm btn-outline-primary">Switch</button>
                                        </form>
                                    {% endif %}
                                </li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p>No sessions available.</p>
                    {% endif %}
                </div>
            </div>
            
            <div class="footer mt-5">
                <p>Regulatory Document Chatbot &copy; 2025</p>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            // Initialize Mermaid with more robust configuration
            mermaid.initialize({
                startOnLoad: true,
                theme: 'default',
                logLevel: 'fatal',
                securityLevel: 'loose',
                flowchart: { 
                    htmlLabels: true,
                    curve: 'basis'
                },
                sequence: {
                    diagramMarginX: 50,
                    diagramMarginY: 10,
                    actorMargin: 50,
                    width: 150,
                    height: 65
                }
            });
            
            // Tab functionality
            function openTab(evt, tabName) {
                var i, tabContent, tabs;
                tabContent = document.getElementsByClassName("tab-content");
                for (i = 0; i < tabContent.length; i++) {
                    tabContent[i].className = tabContent[i].className.replace(" active", "");
                }
                tabs = document.getElementsByClassName("tab");
                for (i = 0; i < tabs.length; i++) {
                    tabs[i].className = tabs[i].className.replace(" active", "");
                }
                document.getElementById(tabName).className += " active";
                evt.currentTarget.className += " active";
                
                // Hide notification when diagrams tab is opened
                if (tabName === 'diagrams-tab') {
                    document.getElementById('diagrams-notification').style.display = 'none';
                    
                    // Force re-render mermaid diagrams when tab is opened
                    try {
                        mermaid.init(undefined, '.mermaid');
                    } catch(e) {
                        console.error("Error re-rendering mermaid diagrams:", e);
                    }
                }
            }
            
            // Scroll chat to bottom
            function scrollChatToBottom() {
                var chatContainer = document.getElementById('chat-messages');
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            // Check if we have a diagram
            function checkAndShowDiagramNotification() {
                var mermaidDivs = document.querySelectorAll('.mermaid');
                if (mermaidDivs.length > 0) {
                    var notificationElement = document.getElementById('diagrams-notification');
                    if (notificationElement) {
                        notificationElement.style.display = 'block';
                    }
                    
                    // Look for special alert in chat messages
                    var botMessages = document.querySelectorAll('.bot-message');
                    for(var i = 0; i < botMessages.length; i++) {
                        if(botMessages[i].innerHTML.includes('Please click on the "Diagrams" tab above')) {
                            // Check if button already exists to avoid duplicates
                            if (!botMessages[i].querySelector('.btn-warning')) {
                                // Add a click helper
                                var helper = document.createElement('button');
                                helper.innerHTML = 'View Diagram';
                                helper.className = 'btn btn-warning mt-2';
                                helper.onclick = function() {
                                    document.getElementById('diagrams-tab-button').click();
                                };
                                botMessages[i].appendChild(helper);
                            }
                        }
                    }
                }
            }
            
            // Function to ensure diagrams are properly rendered
            function initMermaidDiagrams() {
                try {
                    // Clean up any previous mermaid initialization
                    document.querySelectorAll('.mermaid svg').forEach(function(el) {
                        el.remove();
                    });
                    
                    // Reinitialize mermaid
                    mermaid.init(undefined, '.mermaid');
                } catch(e) {
                    console.error("Error initializing mermaid diagrams:", e);
                }
            }
            
            // Call functions when page loads
            window.onload = function() {
                scrollChatToBottom();
                
                // Initialize diagrams with a delay to ensure DOM is fully loaded
                setTimeout(initMermaidDiagrams, 300);
                
                // Show diagram notification
                setTimeout(checkAndShowDiagramNotification, 500);
            };
        </script>
    </body>
    </html>
    """, session_id=session_id, sessions=sessions, chat_history=chat_history, diagrams=diagrams, documents=documents)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'document' not in request.files:
        return redirect('/')
        
    files = request.files.getlist('document')
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            file_path = os.path.join("data_storage/uploads", filename)
            file.save(file_path)
            
            # Process the PDF
            text_chunks = extract_text_from_pdf(file_path)
            save_document_chunks(filename, text_chunks)
    
    return redirect('/')

@app.route('/ask', methods=['POST'])
def ask_question():
    """Handle questions from the user."""
    import threading
    import time
    
    question = request.form.get('question', '')
    
    if not question:
        return redirect('/')
    
    # Save the question immediately to avoid losing it
    answer = "Processing your question..."
    save_chat_history(question, answer)
    
    # Start processing in a separate thread
    def process_question():
        nonlocal question
        
        try:
            # Check if this is a diagram request
            is_diagram_request, diagram_type = detect_diagram_request(question)
            
            # Get document chunks
            chunks = get_all_document_chunks()
            
            if not chunks:
                answer = "Please upload documents first so I can answer your questions based on them."
                update_chat_history(question, answer)
                return
            
            # Create or get vector store
            vector_store = create_vector_store(chunks)
            
            if not vector_store:
                answer = "There was an error processing your documents. Please try again."
                update_chat_history(question, answer)
                return
                
            # Find relevant chunks
            similar_chunks = get_similar_chunks(question, vector_store)
            
            if is_diagram_request:
                # Generate diagram
                if diagram_type is None:
                    diagram_type = "flowchart"  # Default to flowchart if type is None
                    
                success, result = generate_diagram(question, similar_chunks, diagram_type)
                
                if success:
                    mermaid_code, explanation = result
                    # Get the index of this diagram (it's the latest one)
                    diagram_count = len(get_diagrams()) - 1  # -1 because we just added it and indexes are 0-based
                    
                    answer = f"""
                    I've created a {diagram_type} based on your question.
                    
                    **Explanation:** {explanation}
                    
                    <div style="background-color: #ffe8cc; padding: 10px; border-radius: 5px; margin-top: 10px;">
                    <strong>Important:</strong> 
                    <a href="/view_diagram/{diagram_count}" class="btn btn-success mt-2" target="_blank">Click here to view the diagram in a new tab</a>
                    <br>
                    (Or click on the "Diagrams" tab above to access all diagrams.)
                    </div>
                    """
                else:
                    answer = result
            else:
                # Generate text answer with timeout mechanism
                answer = generate_answer(question, similar_chunks)
            
            # Update the chat history with the actual answer
            update_chat_history(question, answer)
            
        except Exception as e:
            # Handle any unexpected errors
            print(f"Error processing question: {e}")
            answer = f"I encountered an error while processing your question. Please try again or try asking a different question."
            update_chat_history(question, answer)
    
    # Helper function to update chat history
    def update_chat_history(question, answer):
        # Get the existing history
        history = get_chat_history()
        
        if history:
            # Remove the last entry (our placeholder)
            history.pop()
            
            # Update storage with the modified history
            session_id = get_current_session()
            if "sessions" in storage and session_id in storage["sessions"]:
                storage["sessions"][session_id]["chat_history"] = history
            
            # Add the new entry with the actual answer
            save_chat_history(question, answer)
    
    # Start processing thread
    threading.Thread(target=process_question).start()
    
    # Return immediately to avoid blocking the user
    return redirect('/')

@app.route('/new_session', methods=['POST'])
def new_session():
    """Create a new session."""
    create_new_session()
    return redirect('/')

@app.route('/switch_session', methods=['POST'])
def switch_session():
    """Switch to a different session."""
    session_id = request.form.get('session_id')
    
    if session_id:
        storage["current_session"] = session_id
        
    return redirect('/')

@app.route('/view_diagram/<int:diagram_index>')
def view_diagram(diagram_index):
    """Show a single diagram on a dedicated page."""
    diagrams = get_diagrams()
    
    if diagram_index >= len(diagrams):
        return "Diagram not found", 404
        
    diagram_code, explanation, diagram_type = diagrams[diagram_index]
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>View Diagram</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }
            .diagram-container {
                margin: 30px 0;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .explanation {
                margin-top: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }
            .diagram-visual {
                margin-top: 30px;
                padding: 20px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <h1>{{ diagram_type|capitalize }} Diagram</h1>
                <a href="/" class="btn btn-primary">Back to Main App</a>
            </div>
            
            <div class="diagram-container">
                <div class="explanation">
                    <h4>Explanation</h4>
                    <p>{{ explanation }}</p>
                </div>
                
                <div class="diagram-visual">
                    <h4>Diagram</h4>
                    <div class="mermaid-diagram" id="mermaid-diagram">{{ diagram_code }}</div>
                    <div id="diagram-error" class="alert alert-danger mt-3" style="display:none;">
                        Error rendering diagram. See raw code below:
                        <pre class="mt-2 p-2 bg-light">{{ diagram_code }}</pre>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                try {
                    // Configure mermaid
                    mermaid.initialize({
                        startOnLoad: false,
                        securityLevel: 'loose',
                        theme: 'default'
                    });
                    
                    // Get diagram code and create element
                    const diagramCode = document.getElementById('mermaid-diagram').textContent.trim();
                    const outputDiv = document.getElementById('mermaid-diagram');
                    
                    // Render the diagram
                    mermaid.render('mermaid-svg', diagramCode)
                        .then(({svg, bindFunctions}) => {
                            outputDiv.innerHTML = svg;
                            if (bindFunctions) bindFunctions();
                        })
                        .catch(error => {
                            console.error("Error rendering diagram:", error);
                            document.getElementById('diagram-error').style.display = 'block';
                        });
                } catch(e) {
                    console.error("Exception in diagram rendering:", e);
                    document.getElementById('diagram-error').style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """, diagram_code=diagram_code, explanation=explanation, diagram_type=diagram_type)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)