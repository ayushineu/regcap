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
- Chat interface similar to ChatGPT

Author: RegCap Team
Version: 1.0.0
"""

import streamlit as st
import os
import time
import uuid
import json
import base64
import pickle
import numpy as np
import faiss
import PyPDF2
from datetime import datetime
import tempfile
import openai
import threading
import re

# Configure OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Initialize storage paths
STORAGE_DIR = "data_storage"
DOCUMENTS_DIR = os.path.join(STORAGE_DIR, "documents")
CHAT_HISTORY_FILE = os.path.join(STORAGE_DIR, "chat_history.pkl")
SESSIONS_FILE = os.path.join(STORAGE_DIR, "sessions.pkl")
DIAGRAMS_FILE = os.path.join(STORAGE_DIR, "diagrams.pkl")
VECTORS_DIR = os.path.join(STORAGE_DIR, "vectors")

# Ensure storage directories exist
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(VECTORS_DIR, exist_ok=True)

# Initialize storage
def load_data(file_path, default=None):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return pickle.load(f)
    return default if default is not None else {}

def save_data(data, file_path):
    with open(file_path, "wb") as f:
        pickle.dump(data, f)

# Load or initialize sessions
def get_or_create_sessions():
    """Load existing sessions or create new session structure."""
    if not os.path.exists(SESSIONS_FILE):
        # Create default session
        sessions = {"default": {"created_at": datetime.now().isoformat()}}
        save_data(sessions, SESSIONS_FILE)
        return sessions
    return load_data(SESSIONS_FILE)

# Get or create document chunks storage
def get_document_chunks():
    """Get document chunks for the current session."""
    session_id = st.session_state.get("current_session", "default")
    documents = {}
    
    # Check for documents in this session's folder
    session_docs_dir = os.path.join(DOCUMENTS_DIR, session_id)
    if os.path.exists(session_docs_dir):
        for filename in os.listdir(session_docs_dir):
            if filename.endswith(".pkl"):
                file_path = os.path.join(session_docs_dir, filename)
                doc_name = filename[:-4]  # Remove .pkl extension
                with open(file_path, "rb") as f:
                    documents[doc_name] = pickle.load(f)
    
    return documents

# Get chat history
def get_chat_history():
    """Get chat history for the current session."""
    session_id = st.session_state.get("current_session", "default")
    history = load_data(CHAT_HISTORY_FILE, {})
    return history.get(session_id, [])

# Save chat history
def save_chat_history(question, answer, has_diagram=False, diagram_code=None, explanation=None):
    """Save a question-answer pair to chat history."""
    session_id = st.session_state.get("current_session", "default")
    
    # Load existing chat history
    history = load_data(CHAT_HISTORY_FILE, {})
    
    # Initialize session history if needed
    if session_id not in history:
        history[session_id] = []
    
    # Add new entry with timestamp
    entry = {
        "question": question,
        "answer": answer,
        "timestamp": datetime.now().isoformat(),
        "has_diagram": has_diagram
    }
    
    # Add diagram if available
    if has_diagram and diagram_code and explanation:
        # Save diagram separately
        save_diagram(diagram_code, explanation)
        # Reference the diagram index in the chat history
        entry["diagram_index"] = len(get_diagrams()) - 1
    
    history[session_id].append(entry)
    
    # Save updated history
    save_data(history, CHAT_HISTORY_FILE)

# Get diagrams
def get_diagrams():
    """Get diagrams for the current session."""
    session_id = st.session_state.get("current_session", "default")
    diagrams = load_data(DIAGRAMS_FILE, {})
    return diagrams.get(session_id, [])

# Save diagram
def save_diagram(diagram_code, explanation, diagram_type="flowchart"):
    """Save a diagram to storage."""
    session_id = st.session_state.get("current_session", "default")
    
    # Load existing diagrams
    diagrams = load_data(DIAGRAMS_FILE, {})
    
    # Initialize session diagrams if needed
    if session_id not in diagrams:
        diagrams[session_id] = []
    
    # Add new diagram
    diagrams[session_id].append((diagram_code, explanation, diagram_type))
    
    # Save updated diagrams
    save_data(diagrams, DIAGRAMS_FILE)

# Create a new session
def create_new_session():
    """Create a new session and return its ID."""
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Load existing sessions
    sessions = get_or_create_sessions()
    
    # Add new session
    sessions[session_id] = {"created_at": datetime.now().isoformat()}
    
    # Save updated sessions
    save_data(sessions, SESSIONS_FILE)
    
    # Create directory for session documents
    os.makedirs(os.path.join(DOCUMENTS_DIR, session_id), exist_ok=True)
    
    return session_id

# Utility functions
def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    text = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_file.getvalue())
        temp_path = temp_file.name
    
    try:
        with open(temp_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return text

def chunk_text(text, chunk_size=1000, overlap=200):
    """Split text into overlapping chunks."""
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # Try to find a period or newline to break on
        if end < text_length:
            # Look for a good breakpoint
            breakpoint = text.rfind(". ", start, end)
            if breakpoint == -1:
                breakpoint = text.rfind("\n", start, end)
            
            if breakpoint != -1 and breakpoint > start:
                end = breakpoint + 1
        
        # Extract chunk and add to list
        chunk = text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        
        # Move start position, accounting for overlap
        start = end - overlap if end < text_length else text_length
    
    return chunks

def get_embedding(text, model="text-embedding-ada-002"):
    """Generate an embedding for a text string using OpenAI API."""
    try:
        text = text.replace("\n", " ")
        response = openai.embeddings.create(
            input=[text],
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        st.error(f"Error generating embedding: {str(e)}")
        return None

def create_vector_store(chunks):
    """Create a FAISS vector store from text chunks."""
    if not chunks:
        return None, []
    
    # Generate embeddings for all chunks
    embeddings = []
    valid_chunks = []
    
    for chunk in chunks:
        embedding = get_embedding(chunk)
        if embedding:
            embeddings.append(embedding)
            valid_chunks.append(chunk)
    
    if not embeddings:
        return None, []
    
    # Convert to numpy array
    embeddings_array = np.array(embeddings, dtype=np.float32)
    
    # Create FAISS index
    dimension = len(embeddings[0])
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    return index, valid_chunks

def get_similar_chunks(query, index, chunks, top_k=5):
    """Find chunks similar to the query in the vector store."""
    if not index or not chunks:
        return []
    
    # Generate query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    # Convert to numpy array
    query_array = np.array([query_embedding], dtype=np.float32)
    
    # Search for similar chunks
    distances, indices = index.search(query_array, min(top_k, len(chunks)))
    
    # Return the most similar chunks
    similar_chunks = [chunks[i] for i in indices[0]]
    return similar_chunks

def generate_answer_with_openai(question, context):
    """Generate an answer using OpenAI."""
    try:
        prompt = f"""
        You are RegCap GPT, an AI specializing in regulatory document analysis.
        Answer the question based solely on the provided context from the user's documents.
        If you cannot answer based on the context, say "I don't have enough information in the uploaded documents to answer this question."
        
        Context from the user's documents:
        {context}
        
        Question: {question}
        
        Answer:
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are RegCap GPT, an AI specializing in regulatory document analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating answer: {str(e)}")
        return f"Sorry, there was an error generating a response: {str(e)}"

def generate_diagram_with_openai(question, context, diagram_type="flowchart"):
    """Generate a Mermaid diagram using OpenAI."""
    try:
        prompt = f"""
        You are RegCap GPT, an AI specializing in regulatory document analysis and visualization.
        Create a Mermaid diagram ({diagram_type}) based on the context from the user's documents.
        
        Context from the user's documents:
        {context}
        
        Request: {question}
        
        Provide your response in two parts:
        1. A brief explanation of the diagram (2-3 sentences)
        2. A well-formed Mermaid diagram code in the {diagram_type} format
        
        Make sure the diagram:
        - Uses proper Mermaid syntax
        - Is not too complex (max 15 nodes)
        - Has clear, concise labels
        - Focuses on key relationships
        - Uses standard Mermaid formatting
        
        Format your response like this:
        Explanation: [Your explanation here]
        
        ```mermaid
        [Your Mermaid diagram code here]
        ```
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are RegCap GPT, an AI specializing in regulatory document analysis and visualization."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        # Extract explanation and diagram
        explanation_match = re.search(r"Explanation:\s*(.*?)(?=```|$)", content, re.DOTALL)
        diagram_match = re.search(r"```mermaid\s*(.*?)```", content, re.DOTALL)
        
        explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided."
        diagram_code = diagram_match.group(1).strip() if diagram_match else ""
        
        # Fix common mermaid syntax issues
        if diagram_code:
            # Ensure proper flowchart declaration
            if diagram_type == "flowchart" and not re.search(r"^(flowchart|graph)", diagram_code):
                diagram_code = f"flowchart TD\n{diagram_code}"
            
            # Remove any multiple consecutive empty lines
            diagram_code = re.sub(r"\n{3,}", "\n\n", diagram_code)
        
        return explanation, diagram_code
    except Exception as e:
        st.error(f"Error generating diagram: {str(e)}")
        return f"Error creating diagram: {str(e)}", ""

def detect_diagram_request(question):
    """Detect if the question is asking for a diagram or visualization."""
    diagram_keywords = [
        "diagram", "visualize", "visualization", "flowchart", "flow chart", 
        "chart", "graph", "map", "process flow", "visual", "visually",
        "show me", "illustrate", "draw"
    ]
    
    # Check if any diagram keyword is in the question
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in diagram_keywords)

def process_uploaded_documents(uploaded_files):
    """Process uploaded PDF documents."""
    if not uploaded_files:
        return
    
    session_id = st.session_state.get("current_session", "default")
    session_docs_dir = os.path.join(DOCUMENTS_DIR, session_id)
    os.makedirs(session_docs_dir, exist_ok=True)
    
    with st.spinner("Processing documents..."):
        for uploaded_file in uploaded_files:
            try:
                # Extract text from PDF
                text = extract_text_from_pdf(uploaded_file)
                
                if not text:
                    st.warning(f"No text could be extracted from {uploaded_file.name}")
                    continue
                
                # Split into chunks
                chunks = chunk_text(text)
                
                # Save chunks to file
                filename = uploaded_file.name.replace(" ", "_")
                file_path = os.path.join(session_docs_dir, f"{filename}.pkl")
                with open(file_path, "wb") as f:
                    pickle.dump(chunks, f)
                
                st.success(f"Processed {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")

def process_question(question):
    """Process a question and generate an answer."""
    # Get document chunks for the current session
    documents = get_document_chunks()
    
    if not documents:
        return "Please upload some documents before asking questions."
    
    # Combine all chunks from all documents
    all_chunks = []
    for doc_chunks in documents.values():
        all_chunks.extend(doc_chunks)
    
    if not all_chunks:
        return "No text content found in the uploaded documents."
    
    # Create vector store
    with st.spinner("Creating vector index..."):
        index, valid_chunks = create_vector_store(all_chunks)
    
    if not index:
        return "Error creating vector index for the documents."
    
    # Find relevant chunks
    with st.spinner("Finding relevant information..."):
        relevant_chunks = get_similar_chunks(question, index, valid_chunks)
    
    if not relevant_chunks:
        return "Couldn't find relevant information in the documents."
    
    # Combine relevant chunks into context
    context = "\n\n".join(relevant_chunks)
    
    # Check if this is a diagram request
    is_diagram_request = detect_diagram_request(question)
    
    # Generate answer or diagram
    if is_diagram_request:
        with st.spinner("Generating diagram..."):
            explanation, diagram_code = generate_diagram_with_openai(question, context)
            # Save to history
            save_chat_history(question, explanation, has_diagram=True, diagram_code=diagram_code, explanation=explanation)
            return explanation, diagram_code
    else:
        with st.spinner("Generating answer..."):
            answer = generate_answer_with_openai(question, context)
            # Save to history
            save_chat_history(question, answer)
            return answer, None

# App UI
def main():
    # Page config
    st.set_page_config(
        page_title="RegCap GPT - Regulatory Document Analysis",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    if "current_session" not in st.session_state:
        st.session_state["current_session"] = "default"
    
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = get_chat_history()
    
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"
    
    # Apply custom CSS
    st.markdown("""
    <style>
    /* Custom styles for a professional look */
    .main-title {
        color: #0088cc;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #666;
        font-style: italic;
        margin-bottom: 2rem;
    }
    .beta-banner {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
        border-left: 5px solid #ffeeba;
    }
    .stButton button {
        width: 100%;
    }
    .session-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
    }
    .chat-user {
        background-color: #e9f5ff;
        border-radius: 15px 15px 3px 15px;
        padding: 12px 18px;
        margin: 8px 0;
        max-width: 80%;
        align-self: flex-end;
        font-size: 16px;
    }
    .chat-assistant {
        background-color: #f0f2f5;
        border-radius: 15px 15px 15px 3px;
        padding: 12px 18px;
        margin: 8px 0;
        max-width: 80%;
        align-self: flex-start;
        font-size: 16px;
    }
    /* Dark mode styles */
    .dark-mode {
        background-color: #1e1e1e;
        color: #f0f0f0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Dark/Light mode toggle
    theme_col1, theme_col2, theme_col3 = st.columns([1, 3, 1])
    with theme_col3:
        if st.button("🌓 Toggle Theme"):
            st.session_state["theme"] = "dark" if st.session_state["theme"] == "light" else "light"
            st.experimental_rerun()

    # Main header
    st.markdown("<h1 class='main-title'>RegCap GPT</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Regulatory Document Analysis Platform</p>", unsafe_allow_html=True)
    
    # Beta Notice
    st.markdown("""
    <div class="beta-banner">
        🚧 <b>Beta Notice:</b> RegCap GPT is currently in active development. 
        Some features may be limited or evolving. Thank you for testing and sharing feedback!
    </div>
    """, unsafe_allow_html=True)

    # Sidebar - Document Management
    with st.sidebar:
        st.header("Document Management")
        
        # Upload section
        st.subheader("Upload Documents")
        uploaded_files = st.file_uploader(
            "Upload regulatory PDF documents",
            type=["pdf"],
            accept_multiple_files=True
        )
        
        if st.button("Process Documents", key="process_docs"):
            process_uploaded_documents(uploaded_files)
        
        # Session management
        st.markdown("---")
        st.subheader("Session Management")
        
        if st.button("Create New Session"):
            new_session_id = create_new_session()
            st.session_state["current_session"] = new_session_id
            st.session_state["chat_history"] = []
            st.success(f"Created new session: {new_session_id}")
            st.experimental_rerun()
        
        # Display available sessions
        sessions = get_or_create_sessions()
        if sessions:
            st.subheader("Available Sessions")
            current_session_id = st.session_state.get("current_session", "default")
            
            for session_id, session_data in sessions.items():
                created_at = datetime.fromisoformat(session_data["created_at"]).strftime("%Y-%m-%d %H:%M")
                
                # Highlight current session
                if session_id == current_session_id:
                    st.markdown(f"""
                    <div class='session-card' style='border-left: 5px solid #0088cc;'>
                        <b>{session_id}</b><br>
                        <small>Created: {created_at}</small><br>
                        <small><i>Current Session</i></small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                        <div class='session-card'>
                            <b>{session_id}</b><br>
                            <small>Created: {created_at}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        if st.button("Switch", key=f"switch_{session_id}"):
                            st.session_state["current_session"] = session_id
                            st.session_state["chat_history"] = get_chat_history()
                            st.success(f"Switched to session: {session_id}")
                            st.experimental_rerun()

    # Main content
    tab1, tab2, tab3 = st.tabs(["Chat", "Documents", "Diagrams"])
    
    # Chat tab
    with tab1:
        st.header("Ask Questions About Your Documents")
        
        # Display chat history
        chat_history = get_chat_history()
        
        for entry in chat_history:
            question = entry["question"]
            answer = entry["answer"]
            
            # Display user question
            st.markdown(f"<div class='chat-user'><b>You:</b> {question}</div>", unsafe_allow_html=True)
            
            # Display assistant response
            st.markdown(f"<div class='chat-assistant'><b>RegCap GPT:</b> {answer}</div>", unsafe_allow_html=True)
            
            # Display diagram if available
            if entry.get("has_diagram") and "diagram_index" in entry:
                diagram_index = entry["diagram_index"]
                diagrams = get_diagrams()
                
                if diagram_index < len(diagrams):
                    diagram_code, explanation, diagram_type = diagrams[diagram_index]
                    st.markdown(f"#### Diagram")
                    st.markdown(diagram_code)
        
        # Input for new questions
        user_question = st.chat_input("Ask a question about your regulatory documents...")
        
        if user_question:
            # Display user question
            st.markdown(f"<div class='chat-user'><b>You:</b> {user_question}</div>", unsafe_allow_html=True)
            
            # Generate and display response
            result = process_question(user_question)
            
            if isinstance(result, tuple) and len(result) == 2:
                answer, diagram_code = result
                
                # Display text answer
                st.markdown(f"<div class='chat-assistant'><b>RegCap GPT:</b> {answer}</div>", unsafe_allow_html=True)
                
                # Display diagram if available
                if diagram_code:
                    st.markdown(f"#### Diagram")
                    st.markdown(f"```mermaid\n{diagram_code}\n```")
            else:
                # This is just a text answer
                st.markdown(f"<div class='chat-assistant'><b>RegCap GPT:</b> {result}</div>", unsafe_allow_html=True)
            
            # Refresh chat history
            st.session_state["chat_history"] = get_chat_history()
    
    # Documents tab
    with tab2:
        st.header("Uploaded Documents")
        
        documents = get_document_chunks()
        if documents:
            st.subheader(f"Documents in Current Session")
            
            for doc_name, chunks in documents.items():
                with st.expander(f"{doc_name} ({len(chunks)} chunks)"):
                    # Display the first chunk as a preview
                    if chunks:
                        st.markdown("**Preview:**")
                        st.markdown(chunks[0][:500] + "...")
                        st.markdown(f"Total content: ~{sum(len(chunk) for chunk in chunks):,} characters")
        else:
            st.info("No documents uploaded in the current session. Use the sidebar to upload documents.")
    
    # Diagrams tab
    with tab3:
        st.header("Generated Diagrams")
        
        diagrams = get_diagrams()
        if diagrams:
            st.subheader(f"Diagrams in Current Session")
            
            for i, (diagram_code, explanation, diagram_type) in enumerate(diagrams):
                with st.expander(f"Diagram {i+1}: {explanation[:50]}..."):
                    st.markdown(f"**Explanation:** {explanation}")
                    st.markdown(f"**Type:** {diagram_type}")
                    st.markdown(f"```mermaid\n{diagram_code}\n```")
        else:
            st.info("No diagrams generated in the current session. Ask a question that includes visualization terms like 'diagram', 'visualize', or 'flowchart'.")
    
    # Footer
    st.markdown("---")
    st.caption("RegCap GPT v1.0.0 | © 2025 RegCap Team | Regulatory Document Analysis Platform")

if __name__ == "__main__":
    main()