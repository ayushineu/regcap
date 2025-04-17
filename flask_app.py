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
# Create a simple in-memory cache for embeddings
embedding_cache = {}

def get_embedding(text):
    """Get embedding for text using OpenAI with caching."""
    try:
        # Clean and standardize the text
        text = text.replace("\n", " ").strip()
        
        # Use a hash of the text as the cache key
        cache_key = hash(text)
        
        # Check if we have a cached embedding
        if cache_key in embedding_cache:
            print(f"Using cached embedding (text length: {len(text)})")
            return embedding_cache[cache_key]
            
        print(f"Generating new embedding for text (length: {len(text)})")
        max_retries = 3  # Reduced number of retries
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                response = client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small",
                    timeout=10  # Add a timeout of 10 seconds
                )
                embedding = np.array(response.data[0].embedding, dtype=np.float32)
                
                # Cache the result
                embedding_cache[cache_key] = embedding
                
                end_time = time.time()
                print(f"Embedding generated in {end_time - start_time:.2f} seconds")
                return embedding
            except Exception as e:
                if "rate_limit_exceeded" in str(e) and attempt < max_retries - 1:
                    print(f"Rate limit exceeded, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"Failed to get embedding on attempt {attempt+1}: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
        
        # If we get here, all retries failed
        print("All embedding attempts failed")
        return None
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def create_vector_store(chunks):
    """Create a FAISS vector store from chunks."""
    if not chunks:
        print("No chunks provided to create vector store")
        return None
        
    try:
        print(f"Creating vector store for {len(chunks)} chunks")
        start_time = time.time()
        
        # Get embeddings for chunks
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = []
        chunk_map = {}  # To keep track of which chunks correspond to which embeddings
        
        # Process in batches to avoid rate limits
        batch_size = 10  # Increased batch size for efficiency
        total_embeddings = 0
        
        print(f"Processing chunks in batches of {batch_size}")
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i+batch_size]
            batch_indices = list(range(i, min(i+batch_size, len(chunk_texts))))
            
            print(f"Processing batch {i//batch_size + 1}/{(len(chunk_texts) + batch_size - 1)//batch_size}: {len(batch)} chunks")
            batch_start = time.time()
            
            # Process each chunk in the batch
            for j, (text, orig_idx) in enumerate(zip(batch, batch_indices)):
                embedding = get_embedding(text)
                if embedding is not None:
                    embeddings.append(embedding)
                    chunk_map[len(embeddings) - 1] = chunks[orig_idx]  # Map embedding index to original chunk
                    total_embeddings += 1
            
            batch_end = time.time()
            print(f"Batch processed in {batch_end - batch_start:.2f} seconds, total embeddings: {total_embeddings}")
        
        # Make sure we have at least one embedding
        if not embeddings:
            print("No valid embeddings were generated.")
            return None
            
        # Create FAISS index
        dimension = len(embeddings[0])
        print(f"Creating FAISS index with dimension {dimension}")
        index = faiss.IndexFlatL2(dimension)
        
        # Make sure all embeddings have the same shape
        filtered_embeddings = []
        filtered_chunks = []
        
        for i, embedding in enumerate(embeddings):
            if len(embedding) == dimension:
                filtered_embeddings.append(embedding)
                filtered_chunks.append(chunk_map[i])
        
        # Make sure we have at least one valid embedding after filtering
        if not filtered_embeddings:
            print("No consistent embeddings were found.")
            return None
        
        print(f"Adding {len(filtered_embeddings)} embeddings to FAISS index")    
        embeddings_array = np.array(filtered_embeddings).astype('float32')
        index.add(embeddings_array)
        
        end_time = time.time()
        print(f"Vector store created in {end_time - start_time:.2f} seconds")
        
        return {
            "index": index,
            "chunks": filtered_chunks,
            "embeddings": embeddings_array
        }
    except Exception as e:
        print(f"Error creating vector store: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_similar_chunks(query, vector_store, top_k=5):
    """Find chunks similar to query in vector store."""
    if not vector_store:
        print("No vector store available for similarity search")
        return []
        
    try:
        print(f"Finding chunks similar to: '{query[:50]}...'")
        start_time = time.time()
        
        # Get embedding for the query
        print("Generating embedding for query...")
        query_embedding = get_embedding(query)
        if query_embedding is None:
            print("Failed to generate embedding for query")
            return []
            
        query_embedding = np.array([query_embedding]).astype('float32')
        print("Query embedding generated successfully")
        
        # Search for similar chunks
        print(f"Searching for top {top_k} similar chunks...")
        distances, indices = vector_store["index"].search(query_embedding, top_k)
        
        # Get the chunks
        similar_chunks = [vector_store["chunks"][idx] for idx in indices[0]]
        
        end_time = time.time()
        print(f"Found {len(similar_chunks)} similar chunks in {end_time - start_time:.2f} seconds")
        
        # Print a preview of the chunks for debugging
        for i, chunk in enumerate(similar_chunks):
            print(f"Chunk {i+1} (distance: {distances[0][i]:.4f}): {chunk['content'][:100]}...")
            
        return similar_chunks
    except Exception as e:
        print(f"Error getting similar chunks: {e}")
        import traceback
        traceback.print_exc()
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
    """Save chat history to storage with timestamp."""
    session_id = get_current_session()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
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
        
        # Add timestamp to the question and answer
        timestamped_question = f"[{timestamp}] {question}"
        timestamped_answer = f"[{timestamp}] {answer}"
        
        storage["sessions"][session_id]["chat_history"].append((timestamped_question, timestamped_answer))
        print(f"Saved chat history with timestamp: {timestamp}")
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

# Logging and status tracking functions
def log_message(message):
    """Add a message to the logs with timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    process_log_storage["logs"].append({
        "timestamp": timestamp,
        "message": message
    })
    print(message)  # Also print to console

def update_question_status(question_id, stage=None, progress=None, done=None, error=None):
    """Update the status of a question being processed."""
    if question_id not in process_log_storage["question_status"]:
        # Initialize with default values
        process_log_storage["question_status"][question_id] = {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "stage": "Starting",
            "progress": 5,
            "done": False,
            "error": None
        }
    
    # Update provided fields
    if stage:
        process_log_storage["question_status"][question_id]["stage"] = stage
        log_message(f"Question {question_id}: {stage}")
    
    if progress is not None:
        process_log_storage["question_status"][question_id]["progress"] = progress
    
    if done is not None:
        process_log_storage["question_status"][question_id]["done"] = done
        if done:
            log_message(f"Question {question_id}: Processing complete")
    
    if error:
        process_log_storage["question_status"][question_id]["error"] = error
        log_message(f"Question {question_id} ERROR: {error}")
    
    return process_log_storage["question_status"][question_id]

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
        <title>RegCap GPT | Regulatory Intelligence</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.css">
        <style>
            :root {
                --bg-color: #ffffff;
                --text-color: #212529;
                --border-color: #ddd;
                --tab-bg: #f5f5f5;
                --tab-active-bg: #007bff;
                --tab-active-color: white;
                --user-msg-bg: #e6f7ff;
                --user-msg-border: #1890ff;
                --bot-msg-bg: #f5f5f5;
                --bot-msg-border: #52c41a;
                --session-bg: #f8f9fa;
                --diagram-bg: #e9f7ef;
                --app-heading: #0056b3;
                --card-bg: #f8f9fa;
                --notification-bg: #ffe8cc;
                --notification-text: #333;
            }
            
            [data-theme="dark"] {
                --bg-color: #212529;
                --text-color: #f8f9fa;
                --border-color: #495057;
                --tab-bg: #343a40;
                --tab-active-bg: #0d6efd;
                --tab-active-color: white;
                --user-msg-bg: #0d47a1;
                --user-msg-border: #42a5f5;
                --bot-msg-bg: #2d2d2d;
                --bot-msg-border: #66bb6a;
                --session-bg: #343a40;
                --diagram-bg: #343a40;
                --app-heading: #42a5f5;
                --card-bg: #343a40;
                --notification-bg: #664500;
                --notification-text: #ffe8cc;
            }
            
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
                background-color: var(--bg-color);
                color: var(--text-color);
                transition: all 0.3s ease;
            }
            .chat-container {
                height: 400px;
                overflow-y: auto;
                padding: 15px 0;
                margin-bottom: 20px;
            }
            .user-message, .bot-message {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            }
            .user-message {
                background-color: var(--user-msg-bg);
                margin-left: 20%;
                border-left: 3px solid var(--user-msg-border);
            }
            .bot-message {
                background-color: var(--bot-msg-bg);
                margin-right: 20%;
                border-left: 3px solid var(--bot-msg-border);
            }
            .document-section, .diagram-section {
                margin-top: 30px;
                padding: 20px;
                border: 1px solid var(--border-color);
                border-radius: 5px;
                background-color: var(--card-bg);
                color: var(--text-color);
            }
            .app-container {
                display: flex;
                min-height: 80vh;
            }
            .tabs {
                display: flex;
                flex-direction: column;
                width: 200px;
                border-right: 1px solid var(--border-color);
                margin-right: 20px;
                padding-right: 10px;
            }
            .tab {
                padding: 15px;
                cursor: pointer;
                background-color: var(--tab-bg);
                border: 1px solid var(--border-color);
                margin-bottom: 5px;
                border-radius: 5px;
                font-weight: bold;
                transition: all 0.3s ease;
                text-align: left;
            }
            .tab.active {
                background-color: var(--tab-active-bg);
                color: var(--tab-active-color);
                border-color: var(--tab-active-bg);
            }
            .tab:hover {
                background-color: #e3e3e3;
            }
            .tab.active:hover {
                background-color: #0069d9;
            }
            [data-theme="dark"] .tab:hover {
                background-color: #4a4a4a;
            }
            [data-theme="dark"] .tab.active:hover {
                background-color: #0069d9;
            }
            #diagrams-tab-button {
                background-color: var(--tab-bg);
                border: 1px solid var(--border-color);
            }
            #diagrams-tab-button.active {
                background-color: var(--tab-active-bg);
                color: var(--tab-active-color);
                border-color: var(--tab-active-bg);
            }
            [data-theme="dark"] #diagrams-tab-button {
                background-color: var(--tab-bg);
                border: 1px solid var(--border-color);
            }
            [data-theme="dark"] #diagrams-tab-button.active {
                background-color: #0069d9;
                color: white;
                border-color: #0069d9;
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
                background-color: var(--session-bg);
                border-radius: 5px;
                border: 1px solid var(--border-color);
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
                border: 1px solid var(--border-color);
                border-radius: 5px;
                background-color: var(--card-bg);
                color: var(--text-color);
            }
            .diagram-code {
                margin-top: 10px;
                padding: 10px;
                background-color: var(--session-bg);
                border-radius: 5px;
                overflow-x: auto;
            }
            .diagram-explanation {
                margin-top: 10px;
                padding: 10px;
                background-color: var(--card-bg);
                color: var(--text-color);
                border-radius: 5px;
            }
            .diagram-visual {
                margin-top: 20px;
                padding: 10px;
                background-color: var(--diagram-bg);
                color: var(--text-color);
                border: 1px solid var(--border-color);
                border-radius: 5px;
            }
            .footer {
                margin-top: 50px;
                text-align: center;
                color: var(--text-color);
                font-size: 0.9rem;
                opacity: 0.7;
            }
            
            /* Dark mode specific bootstrap overrides */
            [data-theme="dark"] .form-control {
                background-color: #333;
                border-color: #555;
                color: #fff;
            }
            [data-theme="dark"] .list-group-item {
                background-color: #333;
                border-color: #555;
                color: #fff;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="mt-4 mb-4 d-flex justify-content-between align-items-center">
                <div>
                    <h1 class="mb-0" style="color: var(--app-heading);">RegCap GPT</h1>
                    <p class="mb-0" style="font-size: 1.1rem; color: var(--text-color); opacity: 0.7;">Regulatory Intelligence</p>
                </div>
                <div>
                    <button id="darkModeToggle" class="btn btn-outline-secondary">
                        <i class="fa fa-moon-o"></i> Dark Mode
                    </button>
                </div>
            </div>
            
            <!-- App Container with Sidebar Tabs -->
            <div class="app-container">
                <!-- Sidebar Tabs -->
                <div class="tabs">
                    <div id="chat-tab-button" class="tab active" onclick="openTab(event, 'chat-tab')">Chat</div>
                    <div id="documents-tab-button" class="tab" onclick="openTab(event, 'documents-tab')">Documents</div>
                    <div id="diagrams-tab-button" class="tab" onclick="openTab(event, 'diagrams-tab')">
                        <span style="position: relative;">
                            Diagrams
                            <div style="position: absolute; top: 3px; right: 5px; background-color: #ff9900; color: white; border-radius: 50%; width: 18px; height: 18px; display: none; font-size: 12px; text-align: center; line-height: 18px;" id="diagrams-notification">!</div>
                        </span>
                    </div>
                    <div id="sessions-tab-button" class="tab" onclick="openTab(event, 'sessions-tab')">Sessions</div>
                </div>
                
                <!-- Tab Content Container -->
                <div class="tab-content-container" style="flex: 1;">
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
                            <strong>Bot:</strong> Welcome to RegCap GPT! I'm your regulatory intelligence assistant. Upload regulatory documents and ask me questions about them.
                        </div>
                    {% endif %}
                </div>
                
                <form action="/ask" method="post" id="question-form">
                    <div class="mb-3">
                        <label for="question" class="form-label">Your Question:</label>
                        <textarea class="form-control" id="question" name="question" rows="3" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary" id="ask-button">Ask</button>
                    <div id="question-status" class="mt-2" style="display: none;">
                        <div class="d-flex align-items-center">
                            <div class="spinner-border spinner-border-sm me-2" role="status">
                                <span class="visually-hidden">Processing...</span>
                            </div>
                            <span>Processing your question...</span>
                        </div>
                    </div>
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
                    <div class="mb-4">
                        <h3>Current Session</h3>
                        <div class="session-info">
                            <h5>Active Session: {{ session_id }}</h5>
                            <button id="createNewSessionBtn" class="btn btn-primary mt-2">Create New Session</button>
                        </div>
                    </div>
                    
                    <h3>Available Sessions</h3>
                    {% if sessions %}
                        <ul class="list-group">
                            {% for s_id, created_at in sessions.items() %}
                                <li class="list-group-item d-flex justify-content-between align-items-center">
                                    {{ s_id }} 
                                    {% if s_id == session_id %}
                                        <span class="badge bg-primary rounded-pill">Current</span>
                                    {% else %}
                                        <button class="btn btn-sm btn-outline-primary switch-session-btn" data-session-id="{{ s_id }}">Switch</button>
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
            </div>
            
            <div class="footer mt-5">
                <p>RegCap GPT &copy; 2025 | Regulatory Intelligence</p>
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
            
            // Auto-refresh was removed from here because it was causing issues
            // with constant page refreshes
            
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
            
            // Dark mode toggle functionality
            function setupDarkModeToggle() {
                const darkModeToggle = document.getElementById('darkModeToggle');
                const htmlElement = document.documentElement;
                
                // Check for saved theme preference or respect OS preference
                const savedTheme = localStorage.getItem('theme');
                const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
                
                // Apply dark theme if saved or OS prefers dark
                if (savedTheme === 'dark' || (!savedTheme && prefersDarkMode)) {
                    htmlElement.setAttribute('data-theme', 'dark');
                    darkModeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                    // Update Mermaid theme
                    mermaid.initialize({ theme: 'dark' });
                }
                
                // Toggle theme when button is clicked
                darkModeToggle.addEventListener('click', function() {
                    if (htmlElement.getAttribute('data-theme') === 'dark') {
                        htmlElement.removeAttribute('data-theme');
                        localStorage.setItem('theme', 'light');
                        darkModeToggle.innerHTML = '<i class="fa fa-moon-o"></i> Dark Mode';
                        // Update Mermaid theme
                        mermaid.initialize({ theme: 'default' });
                    } else {
                        htmlElement.setAttribute('data-theme', 'dark');
                        localStorage.setItem('theme', 'dark');
                        darkModeToggle.innerHTML = '<i class="fa fa-sun-o"></i> Light Mode';
                        // Update Mermaid theme
                        mermaid.initialize({ theme: 'dark' });
                    }
                    
                    // Reinitialize Mermaid diagrams with the new theme
                    try {
                        setTimeout(function() {
                            initMermaidDiagrams();
                        }, 100);
                    } catch (error) {
                        console.error("Error updating Mermaid diagrams after theme change:", error);
                    }
                });
            }
            
            // Session management via AJAX
            function setupSessionManagement() {
                // Create new session
                const createNewSessionBtn = document.getElementById('createNewSessionBtn');
                if (createNewSessionBtn) {
                    createNewSessionBtn.addEventListener('click', function() {
                        // Display loading state
                        createNewSessionBtn.disabled = true;
                        createNewSessionBtn.innerHTML = 'Creating...';
                        
                        // Send AJAX request
                        fetch('/new_session', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        })
                        .then(response => {
                            if (response.ok) {
                                // Refresh only the content, not the entire page
                                window.location.href = '/?t=' + new Date().getTime();
                            }
                        })
                        .catch(error => {
                            console.error('Error creating new session:', error);
                            createNewSessionBtn.disabled = false;
                            createNewSessionBtn.innerHTML = 'Create New Session';
                        });
                    });
                }
                
                // Setup switch session buttons
                const switchButtons = document.querySelectorAll('.switch-session-btn');
                switchButtons.forEach(function(button) {
                    button.addEventListener('click', function() {
                        const sessionId = this.getAttribute('data-session-id');
                        
                        // Display loading state
                        button.disabled = true;
                        button.innerHTML = 'Switching...';
                        
                        // Create form data
                        const formData = new FormData();
                        formData.append('session_id', sessionId);
                        
                        // Send AJAX request
                        fetch('/switch_session', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => {
                            if (response.ok) {
                                // Refresh only the content, not the entire page
                                window.location.href = '/?t=' + new Date().getTime();
                            }
                        })
                        .catch(error => {
                            console.error('Error switching session:', error);
                            button.disabled = false;
                            button.innerHTML = 'Switch';
                        });
                    });
                });
            }
            
            // Setup AJAX form submission for questions
            function setupQuestionFormAjax() {
                const questionForm = document.getElementById('question-form');
                const askButton = document.getElementById('ask-button');
                const statusDiv = document.getElementById('question-status');
                const questionInput = document.getElementById('question');
                
                if (questionForm) {
                    questionForm.addEventListener('submit', function(e) {
                        e.preventDefault(); // Prevent regular form submission
                        
                        const question = questionInput.value.trim();
                        if (!question) return; // Don't submit empty questions
                        
                        // Show loading status and disable button
                        askButton.disabled = true;
                        statusDiv.style.display = 'block';
                        
                        // Create the form data from the question
                        const formData = new FormData();
                        formData.append('question', question);
                        
                        // Send AJAX request with x-requested-with header
                        fetch('/ask', {
                            method: 'POST',
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest'
                            },
                            body: formData
                        })
                        .then(response => {
                            if (response.ok) {
                                return response.json().then(data => {
                                    console.log('Question submitted:', data);
                                    
                                    // Add placeholder message to the chat
                                    const chatMessages = document.getElementById('chat-messages');
                                    const userMsg = document.createElement('div');
                                    userMsg.className = 'message user-message';
                                    userMsg.textContent = question;
                                    chatMessages.appendChild(userMsg);
                                    
                                    const botMsg = document.createElement('div');
                                    botMsg.className = 'message bot-message';
                                    botMsg.innerHTML = '<div class="processing-message">Processing your question... <div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
                                    chatMessages.appendChild(botMsg);
                                    
                                    // Set up status polling if we have a question ID
                                    if (data.question_id) {
                                        startStatusPolling(data.question_id, botMsg);
                                    }
                                    
                                    scrollChatToBottom();
                                    
                                    // Clear input
                                    questionInput.value = '';
                                    
                                    // Simply re-enable the button after a delay
                                    setTimeout(function() {
                                        askButton.disabled = false;
                                        statusDiv.style.display = 'none';
                                    
                                    // Add a small refresh button next to the "Processing" text in the chat
                                    const processingMsgs = document.querySelectorAll('.processing-message');
                                    processingMsgs.forEach(msg => {
                                        // Only add refresh button if it doesn't already have one
                                        if (!msg.querySelector('.refresh-btn')) {
                                            const refreshBtn = document.createElement('button');
                                            refreshBtn.className = 'btn btn-sm btn-outline-primary refresh-btn ms-2';
                                            refreshBtn.innerHTML = '<i class="fa fa-refresh"></i>';
                                            refreshBtn.title = "Check for answer";
                                            refreshBtn.onclick = function() { window.location.reload(); };
                                            msg.appendChild(refreshBtn);
                                        }
                                    });
                                }, 1500);
                            } else {
                                console.error('Failed to submit question');
                                statusDiv.textContent = 'Error submitting question. Please try again.';
                                askButton.disabled = false;
                            }
                        })
                        .catch(error => {
                            console.error('Error submitting question:', error);
                            statusDiv.textContent = 'Error: ' + error.message;
                            askButton.disabled = false;
                        });
                    });
                }
            }
            
            // Function to poll for status updates
            function startStatusPolling(questionId, botMsg) {
                console.log('Starting status polling for question:', questionId);
                
                // Add status indicator to the bot message
                const statusDiv = document.createElement('div');
                statusDiv.className = 'status-indicator mt-2';
                statusDiv.innerHTML = `
                    <div class="card p-2 bg-light">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="status-text small">Initializing...</span>
                            <span class="status-percentage badge bg-primary">5%</span>
                        </div>
                        <div class="progress mt-1" style="height: 4px;">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                 role="progressbar" style="width: 5%;" 
                                 aria-valuenow="5" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                    </div>
                `;
                
                botMsg.appendChild(statusDiv);
                
                const statusText = statusDiv.querySelector('.status-text');
                const statusPercentage = statusDiv.querySelector('.status-percentage');
                const progressBar = statusDiv.querySelector('.progress-bar');
                
                let pollCount = 0;
                let lastStage = '';
                
                // Set up the polling interval
                const pollInterval = setInterval(() => {
                    pollCount++;
                    
                    // Check the status
                    fetch(`/get_question_status/${questionId}`)
                    .then(response => response.json())
                    .then(status => {
                        console.log('Question status:', status);
                        
                        // Update the UI with the status
                        if (status.stage && status.stage !== lastStage) {
                            statusText.innerText = status.stage;
                            lastStage = status.stage;
                        }
                        
                        if (status.progress !== undefined) {
                            const progress = status.progress;
                            statusPercentage.innerText = `${progress}%`;
                            progressBar.style.width = `${progress}%`;
                            progressBar.setAttribute('aria-valuenow', progress);
                            
                            // Update color based on progress
                            if (progress > 75) {
                                progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-success';
                            } else if (progress > 50) {
                                progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-info';
                            }
                        }
                        
                        // If the question is done processing or there's an error, stop polling
                        if (status.done || status.error) {
                            console.log('Question processing complete:', status);
                            clearInterval(pollInterval);
                            
                            // Set final status display
                            if (status.error) {
                                statusDiv.querySelector('.card').className = 'card p-2 bg-danger-subtle';
                                statusText.className = 'status-text small text-danger';
                                statusText.innerText = status.error;
                            } else {
                                // If done successfully, hide the status after a few seconds
                                setTimeout(() => {
                                    statusDiv.style.display = 'none';
                                }, 3000);
                            }
                            
                            // Refresh the page to show the answer
                            setTimeout(() => {
                                window.location.reload();
                            }, 1000);
                        }
                    })
                    .catch(error => {
                        console.error('Error polling status:', error);
                        // Don't stop polling on error, just log it
                    });
                    
                    // If we've been polling for a long time without completion,
                    // still reload but at a slower interval (after 30 seconds)
                    if (pollCount > 60) { // 30 seconds (if polling every 500ms)
                        clearInterval(pollInterval);
                        console.log('Polling timeout reached, refreshing page');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    }
                }, 500); // Poll every 500ms
            }
            
            // Call functions when page loads
            window.onload = function() {
                scrollChatToBottom();
                
                // Initialize diagrams with a delay to ensure DOM is fully loaded
                setTimeout(initMermaidDiagrams, 300);
                
                // Show diagram notification
                setTimeout(checkAndShowDiagramNotification, 500);
                
                // Setup dark mode toggle
                setupDarkModeToggle();
                
                // Setup session management
                setupSessionManagement();
                
                // Setup AJAX question form
                setupQuestionFormAjax();
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
    import uuid
    
    question = request.form.get('question', '')
    
    if not question:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "Question is required"}), 400
        else:
            return redirect('/')
    
    # Generate a unique ID for this question
    question_id = str(uuid.uuid4())
    
    # Initialize question status
    update_question_status(question_id, stage="Initialized", progress=5)
    log_message(f"New question received: '{question[:50]}...' (ID: {question_id})")
    
    # Save the question immediately to avoid losing it
    answer = "<div class='processing-message'>Processing your question... <div class='spinner-border spinner-border-sm text-primary' role='status'><span class='visually-hidden'>Loading...</span></div></div>"
    save_chat_history(question, answer)
    
    # If this is an AJAX request, return success immediately with the question ID
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            "success": True, 
            "message": "Processing question in background",
            "question_id": question_id
        })
    
    # Start processing in a separate thread
    def process_question():
        nonlocal question
        nonlocal question_id
        
        try:
            update_question_status(question_id, stage="Starting question processing", progress=10)
            
            # Check if this is a diagram request
            update_question_status(question_id, stage="Checking if diagram request", progress=15)
            is_diagram_request, diagram_type = detect_diagram_request(question)
            log_message(f"Question {question_id}: Diagram request: {is_diagram_request}, type: {diagram_type}")
            
            # Get document chunks
            update_question_status(question_id, stage="Loading document chunks", progress=20)
            chunks = get_all_document_chunks()
            log_message(f"Question {question_id}: Found {len(chunks) if chunks else 0} document chunks")
            
            if not chunks:
                answer = "Please upload documents first so I can answer your questions based on them."
                update_chat_history(question, answer)
                update_question_status(question_id, stage="Failed - No documents", progress=100, done=True, 
                                     error="No document chunks found")
                return
            
            # Create or get vector store
            update_question_status(question_id, stage="Creating vector store and computing embeddings", progress=30)
            vector_store = create_vector_store(chunks)
            log_message(f"Question {question_id}: Vector store created: {vector_store is not None}")
            
            if not vector_store:
                answer = "There was an error processing your documents. Please try again."
                update_chat_history(question, answer)
                update_question_status(question_id, stage="Failed - Vector store error", progress=100, done=True,
                                     error="Error creating vector store")
                return
                
            # Find relevant chunks
            update_question_status(question_id, stage="Finding similar chunks", progress=60)
            similar_chunks = get_similar_chunks(question, vector_store)
            log_message(f"Question {question_id}: Found {len(similar_chunks)} similar chunks")
            
            if is_diagram_request:
                # Generate diagram
                update_question_status(question_id, stage="Generating diagram", progress=75)
                if diagram_type is None:
                    diagram_type = "flowchart"  # Default to flowchart if type is None
                
                log_message(f"Question {question_id}: Generating {diagram_type} diagram")
                success, result = generate_diagram(question, similar_chunks, diagram_type)
                
                if success:
                    mermaid_code, explanation = result
                    log_message(f"Question {question_id}: Diagram generated successfully")
                    
                    # Sanitize the mermaid code to ensure consistent syntax
                    if diagram_type == "flowchart":
                        # Fix mixed flowchart TD and graph TD syntax
                        if "flowchart TD" in mermaid_code and "graph TD" in mermaid_code:
                            mermaid_code = mermaid_code.replace("graph TD", "")
                        elif "graph TD" in mermaid_code and not mermaid_code.strip().startswith("graph TD"):
                            mermaid_code = mermaid_code.replace("graph TD;", "")
                    
                    # Get the index of this diagram (it's the latest one)
                    diagram_count = len(get_diagrams()) - 1  # -1 because we just added it and indexes are 0-based
                    
                    answer = f"""
                    I've created a {diagram_type} based on your question.
                    
                    **Explanation:** {explanation}
                    
                    <div style="background-color: var(--notification-bg, #ffe8cc); padding: 10px; border-radius: 5px; margin-top: 10px; color: var(--notification-text, #333);">
                    <strong>Important:</strong> 
                    <a href="/view_diagram/{diagram_count}" class="btn btn-success mt-2" target="_blank">Click here to view the diagram in a new tab</a>
                    <br>
                    (Or click on the "Diagrams" tab above to access all diagrams.)
                    </div>
                    """
                    update_question_status(question_id, stage="Complete - Diagram generated", progress=100, done=True)
                else:
                    answer = result
                    update_question_status(question_id, stage="Failed - Diagram generation error", progress=100, done=True, 
                                         error=f"Error generating diagram: {result}")
            else:
                # Generate text answer
                update_question_status(question_id, stage="Generating answer from OpenAI", progress=75)
                log_message(f"Question {question_id}: Generating text answer")
                
                # Track the start time to measure how long the API call takes
                start_time = time.time()
                answer = generate_answer(question, similar_chunks)
                elapsed_time = time.time() - start_time
                
                log_message(f"Question {question_id}: Answer generated in {elapsed_time:.2f} seconds")
                update_question_status(question_id, stage="Complete - Answer generated", progress=100, done=True)
            
            # Update the chat history with the actual answer
            update_chat_history(question, answer)
            
        except Exception as e:
            # Handle any unexpected errors
            error_message = f"Error processing question: {e}"
            log_message(f"Question {question_id} ERROR: {error_message}")
            update_question_status(question_id, stage="Failed - Unexpected error", progress=100, 
                                 done=True, error=error_message)
            
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
    
    # Check if request wants JSON response (from AJAX)
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({"success": True}), 200
    else:
        return redirect('/')

@app.route('/switch_session', methods=['POST'])
def switch_session():
    """Switch to a different session."""
    session_id = request.form.get('session_id')
    
    if session_id:
        storage["current_session"] = session_id
    
    # Check if request wants JSON response (from AJAX)
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({"success": True}), 200
    else:
        return redirect('/')

@app.route('/view_diagram/<int:diagram_index>')
def view_diagram(diagram_index):
    """Show a single diagram on a dedicated page."""
    diagrams = get_diagrams()
    
    if diagram_index >= len(diagrams):
        return "Diagram not found", 404
        
    diagram_code, explanation, diagram_type = diagrams[diagram_index]
    
    # Sanitize the mermaid code to ensure consistent syntax
    if diagram_type == "flowchart":
        # Fix mixed flowchart TD and graph TD syntax
        if "flowchart TD" in diagram_code and "graph TD" in diagram_code:
            diagram_code = diagram_code.replace("graph TD", "")
        elif "graph TD" in diagram_code and not diagram_code.strip().startswith("graph TD"):
            diagram_code = diagram_code.replace("graph TD;", "")
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RegCap GPT - View Diagram</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css" rel="stylesheet">
        <style>
            :root {
                --bg-color: #ffffff;
                --text-color: #333333;
                --app-heading: #0056b3;
                --card-bg: #f8f9fa;
                --border-color: #ddd;
                --diagram-bg: #ffffff;
                --notification-bg: #ffe8cc;
                --notification-text: #333;
            }
            
            [data-theme="dark"] {
                --bg-color: #1e1e1e;
                --text-color: #e0e0e0;
                --app-heading: #4d94ff;
                --card-bg: #2d2d2d;
                --border-color: #444;
                --diagram-bg: #2d2d2d;
                --notification-bg: #664500;
                --notification-text: #ffe8cc;
            }
            
            body {
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
                background-color: var(--bg-color);
                color: var(--text-color);
            }
            
            .diagram-container {
                margin: 30px 0;
                padding: 20px;
                border: 1px solid var(--border-color);
                border-radius: 5px;
                background-color: var(--card-bg);
            }
            
            .explanation {
                margin-top: 20px;
                padding: 15px;
                background-color: var(--card-bg);
                border-radius: 5px;
            }
            
            .diagram-visual {
                margin-top: 30px;
                padding: 20px;
                background-color: var(--diagram-bg);
                border: 1px solid var(--border-color);
                border-radius: 5px;
            }
            
            h1, h4 {
                color: var(--app-heading);
            }
            
            .btn-outline-secondary {
                color: var(--text-color);
                border-color: var(--border-color);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <h1>{{ diagram_type|capitalize }} Diagram</h1>
                <div>
                    <button id="darkModeToggle" class="btn btn-outline-secondary me-2">
                        <i class="fa fa-moon-o"></i> Dark Mode
                    </button>
                    <a href="/" class="btn btn-primary">Back to Main App</a>
                </div>
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
                // Setup dark mode toggle
                setupDarkModeToggle();
                
                // Initialize the diagram
                initializeDiagram();
            });
            
            // Use the existing setupDarkModeToggle function
            
            // Function to initialize the diagram
            function initializeDiagram() {
                try {
                    // Configure mermaid
                    mermaid.initialize({
                        startOnLoad: false,
                        securityLevel: 'loose',
                        theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default'
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
            }
        </script>
    </body>
    </html>
    """, diagram_code=diagram_code, explanation=explanation, diagram_type=diagram_type)

# Logs storage
process_log_storage = {
    "logs": [],
    "question_status": {}
}

@app.route('/get_question_status/<question_id>', methods=['GET'])
def get_question_status(question_id):
    """Get the status of a specific question."""
    if question_id in process_log_storage["question_status"]:
        return jsonify(process_log_storage["question_status"][question_id])
    else:
        return jsonify({"error": "Question not found", "done": True})

@app.route('/debug_api', methods=['GET'])
def debug_api():
    """Check OpenAI API connection."""
    # Import the OpenAI key status
    api_key = os.environ.get("OPENAI_API_KEY")
    api_key_status = "Present" if api_key else "Missing"
    
    try:
        # Test a simple API call with timeout
        response = client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
            timeout=10
        )
        
        return f"""
        <h1>API Debug Information</h1>
        <p>API Key Status: {api_key_status}</p>
        <p>API Connection: Working</p>
        <p>Response: {response.choices[0].message.content}</p>
        <p>Current Time: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}</p>
        """
    except Exception as e:
        return f"""
        <h1>API Debug Information</h1>
        <p>API Key Status: {api_key_status}</p>
        <p>API Connection: Error</p>
        <p>Error Details: {str(e)}</p>
        <p>Current Time: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}</p>
        """
        
@app.route('/logs', methods=['GET'])
def view_logs():
    """View system logs."""
    # Get up to 500 most recent logs (to avoid overwhelming the browser)
    logs = process_log_storage["logs"][-500:] if process_log_storage["logs"] else []
    
    # Get current status of questions being processed
    active_questions = []
    for q_id, status in process_log_storage["question_status"].items():
        if not status.get("done", False):
            active_questions.append({
                "id": q_id,
                "stage": status.get("stage", "Unknown"),
                "progress": status.get("progress", 0),
                "start_time": status.get("start_time", "Unknown")
            })
    
    # Create a readable timestamp with seconds precision
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RegCap GPT - System Logs</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <meta http-equiv="refresh" content="5"> <!-- Auto-refresh every 5 seconds -->
        <style>
            body {
                padding: 20px;
            }
            .log-container {
                height: 600px;
                overflow: auto;
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                font-family: monospace;
            }
            .log-entry {
                margin-bottom: 5px;
            }
            .log-entry:hover {
                background-color: #e9ecef;
            }
            .timestamp {
                color: #6c757d;
                margin-right: 10px;
            }
            .active-question {
                background-color: #d1e7dd;
                border: 1px solid #badbcc;
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">RegCap GPT - System Logs</h1>
            <div class="mb-3">
                <p class="lead">Current time: <span class="fw-bold">{{ current_time }}</span></p>
                <a href="/" class="btn btn-primary mb-3">Back to Main App</a>
                <button class="btn btn-secondary mb-3 ms-2" onClick="window.location.reload();">Refresh Logs</button>
            </div>
            
            <h2>Active Questions ({{ active_questions|length }})</h2>
            {% if active_questions %}
                {% for question in active_questions %}
                <div class="active-question">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>ID:</strong> {{ question.id }}
                            <strong class="ms-3">Stage:</strong> {{ question.stage }}
                            <strong class="ms-3">Start Time:</strong> {{ question.start_time }}
                        </div>
                        <div class="badge bg-primary">{{ question.progress }}%</div>
                    </div>
                    <div class="progress mt-2" style="height: 10px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" 
                             style="width: {{ question.progress }}%;" aria-valuenow="{{ question.progress }}" 
                             aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p>No questions currently being processed.</p>
            {% endif %}
            
            <h2>System Logs</h2>
            <div class="log-container">
                {% if logs %}
                    {% for log in logs %}
                        <div class="log-entry">
                            <span class="timestamp">{{ log.timestamp }}</span>
                            <span class="message">{{ log.message }}</span>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>No logs available.</p>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    """, logs=logs, active_questions=active_questions, current_time=current_time)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)