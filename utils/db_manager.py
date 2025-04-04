import json
import pickle
import base64
import time
import os

# Use simple file-based storage instead of Replit DB
# This avoids potential issues with the Replit DB
class SimpleStorage:
    def __init__(self):
        self.storage_dir = os.path.join(os.getcwd(), "data_storage")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.data = self._load_data()
    
    def _load_data(self):
        data_file = os.path.join(self.storage_dir, "data.json")
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_data(self):
        data_file = os.path.join(self.storage_dir, "data.json")
        with open(data_file, 'w') as f:
            json.dump(self.data, f)
    
    def __getitem__(self, key):
        return self.data.get(key, {})
    
    def __setitem__(self, key, value):
        self.data[key] = value
        self._save_data()
    
    def __contains__(self, key):
        return key in self.data

# Initialize the simple storage
db = SimpleStorage()

def init_db():
    """
    Initialize the database with required collections if they don't exist.
    """
    # Initialize document storage
    if "documents" not in db:
        db["documents"] = {}
    
    # Initialize chat history storage
    if "chat_histories" not in db:
        db["chat_histories"] = {}
    
    # Initialize diagrams storage
    if "diagrams" not in db:
        db["diagrams"] = {}
    
    # Initialize session timestamp
    if "current_session" not in db:
        db["current_session"] = str(int(time.time()))
    
    return db["current_session"]

def get_current_session():
    """
    Get or create the current session ID.
    """
    if "current_session" not in db:
        db["current_session"] = str(int(time.time()))
    
    return db["current_session"]

def create_new_session():
    """
    Create a new session and return its ID.
    """
    new_session_id = str(int(time.time()))
    db["current_session"] = new_session_id
    return new_session_id

def encode_for_storage(obj):
    """
    Encode complex objects for storage in Replit DB.
    """
    return base64.b64encode(pickle.dumps(obj)).decode('utf-8')

def decode_from_storage(encoded_obj):
    """
    Decode complex objects from Replit DB storage.
    """
    if not encoded_obj:
        return None
    return pickle.loads(base64.b64decode(encoded_obj.encode('utf-8')))

# Document Storage Functions
def save_document_chunks(document_name, text_chunks):
    """
    Save document chunks to the database.
    
    Args:
        document_name: Name of the document
        text_chunks: List of extracted text chunks
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        session_id = get_current_session()
        
        if "documents" not in db:
            db["documents"] = {}
        
        if session_id not in db["documents"]:
            db["documents"][session_id] = {}
        
        # Store document chunks
        db["documents"][session_id][document_name] = encode_for_storage(text_chunks)
        return True
    except Exception as e:
        print(f"Error saving document chunks: {str(e)}")
        return False

def get_document_chunks(session_id=None):
    """
    Get all document chunks for a session.
    
    Args:
        session_id: ID of the session to retrieve documents from (default: current session)
    
    Returns:
        Dictionary of document chunks by document name
    """
    try:
        if session_id is None:
            session_id = get_current_session()
        
        if "documents" not in db or session_id not in db["documents"]:
            return {}
        
        # Get document chunks for the session
        documents = {}
        for doc_name, encoded_chunks in db["documents"][session_id].items():
            chunks = decode_from_storage(encoded_chunks)
            if chunks:
                documents[doc_name] = chunks
        
        return documents
    except Exception as e:
        print(f"Error retrieving document chunks: {str(e)}")
        return {}

def get_all_document_chunks(session_id=None):
    """
    Get a flat list of all document chunks for a session.
    
    Args:
        session_id: ID of the session to retrieve documents from (default: current session)
    
    Returns:
        List of all text chunks from all documents
    """
    try:
        if session_id is None:
            session_id = get_current_session()
        
        documents = get_document_chunks(session_id)
        all_chunks = []
        
        for doc_name, chunks in documents.items():
            if chunks:  # Make sure chunks is not None
                all_chunks.extend(chunks)
        
        return all_chunks
    except Exception as e:
        print(f"Error retrieving all document chunks: {str(e)}")
        return []

# Chat History Functions
def save_chat_history(chat_history):
    """
    Save chat history to the database.
    
    Args:
        chat_history: List of (question, answer) tuples
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        session_id = get_current_session()
        
        if "chat_histories" not in db:
            db["chat_histories"] = {}
        
        # Store chat history
        db["chat_histories"][session_id] = encode_for_storage(chat_history)
        return True
    except Exception as e:
        print(f"Error saving chat history: {str(e)}")
        return False

def get_chat_history(session_id=None):
    """
    Get chat history for a session.
    
    Args:
        session_id: ID of the session to retrieve chat history from (default: current session)
    
    Returns:
        List of (question, answer) tuples
    """
    if session_id is None:
        session_id = get_current_session()
    
    if "chat_histories" not in db or session_id not in db["chat_histories"]:
        return []
    
    # Get chat history for the session
    return decode_from_storage(db["chat_histories"][session_id]) or []

# Diagram Functions
def save_diagrams(diagrams):
    """
    Save diagrams to the database.
    
    Args:
        diagrams: List of (diagram_code, explanation, diagram_type) tuples
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        session_id = get_current_session()
        
        if "diagrams" not in db:
            db["diagrams"] = {}
        
        # Store diagrams
        db["diagrams"][session_id] = encode_for_storage(diagrams)
        return True
    except Exception as e:
        print(f"Error saving diagrams: {str(e)}")
        return False

def get_diagrams(session_id=None):
    """
    Get diagrams for a session.
    
    Args:
        session_id: ID of the session to retrieve diagrams from (default: current session)
    
    Returns:
        List of (diagram_code, explanation, diagram_type) tuples
    """
    if session_id is None:
        session_id = get_current_session()
    
    if "diagrams" not in db or session_id not in db["diagrams"]:
        return []
    
    # Get diagrams for the session
    return decode_from_storage(db["diagrams"][session_id]) or []

# Save Vector Store
def save_vector_store(vector_store):
    """
    Save vector store to the database.
    
    Args:
        vector_store: Vector store object
    """
    try:
        session_id = get_current_session()
        
        if "vector_stores" not in db:
            db["vector_stores"] = {}
        
        # Only store the chunks portion of the vector store
        # We'll recreate the index when needed rather than storing the entire FAISS index
        if vector_store and "chunks" in vector_store:
            chunks_to_store = vector_store["chunks"]
            db["vector_stores"][session_id] = encode_for_storage(chunks_to_store)
            return True
        return False
    except Exception as e:
        print(f"Error saving vector store: {str(e)}")
        return False

def get_vector_store(session_id=None):
    """
    Get vector store for a session.
    
    Args:
        session_id: ID of the session to retrieve vector store from (default: current session)
    
    Returns:
        Vector store object if found, None otherwise
    """
    try:
        from utils.vector_store import get_embedding
        import numpy as np
        import faiss
        
        if session_id is None:
            session_id = get_current_session()
        
        if "vector_stores" not in db or session_id not in db["vector_stores"]:
            return None
        
        # Get stored chunks
        stored_chunks = decode_from_storage(db["vector_stores"][session_id])
        
        if not stored_chunks:
            return None
        
        # Generate embeddings for the chunks
        embeddings = []
        for chunk in stored_chunks:
            embedding = get_embedding(chunk["content"])
            if embedding is not None:
                embeddings.append(embedding)
        
        if not embeddings:
            return None
            
        # Convert to numpy array and create FAISS index
        embeddings_array = np.array(embeddings).astype('float32')
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        # Return reconstructed vector store
        return {
            "index": index,
            "chunks": stored_chunks,
            "embeddings": embeddings_array
        }
    except Exception as e:
        print(f"Error retrieving vector store: {str(e)}")
        return None

# Session Management
def list_all_sessions():
    """
    List all available sessions.
    
    Returns:
        Dictionary mapping session IDs to creation timestamps
    """
    all_sessions = {}
    
    # Collect sessions from documents
    if "documents" in db:
        for session_id in db["documents"]:
            all_sessions[session_id] = session_id
    
    # Collect sessions from chat histories
    if "chat_histories" in db:
        for session_id in db["chat_histories"]:
            all_sessions[session_id] = session_id
    
    # Convert timestamps to readable dates
    return {
        session_id: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(ts)))
        for session_id, ts in all_sessions.items()
    }

def delete_session(session_id):
    """
    Delete a session and all its data.
    
    Args:
        session_id: ID of the session to delete
    """
    # Delete documents
    if "documents" in db and session_id in db["documents"]:
        del db["documents"][session_id]
    
    # Delete chat history
    if "chat_histories" in db and session_id in db["chat_histories"]:
        del db["chat_histories"][session_id]
    
    # Delete diagrams
    if "diagrams" in db and session_id in db["diagrams"]:
        del db["diagrams"][session_id]
    
    # Delete vector store
    if "vector_stores" in db and session_id in db["vector_stores"]:
        del db["vector_stores"][session_id]