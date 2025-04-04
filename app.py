import streamlit as st
import os
import time
import datetime
from utils.pdf_processor import extract_text_from_pdfs
from utils.vector_store import create_vector_store, get_similar_chunks
from utils.openai_helper import generate_answer, generate_diagram, detect_diagram_request
from utils.db_manager import (
    init_db, get_current_session, create_new_session, 
    save_document_chunks, get_all_document_chunks, save_chat_history, 
    get_chat_history, save_diagrams, get_diagrams, save_vector_store, 
    get_vector_store, list_all_sessions, delete_session
)

# Set page configuration
st.set_page_config(
    page_title="Regulatory Document Chatbot",
    page_icon="📚",
    layout="wide"
)

# Initialize database
current_session = init_db()

# Initialize session state variables
if "vector_store" not in st.session_state:
    # Try to load from database
    vector_store = get_vector_store()
    st.session_state["vector_store"] = vector_store
    st.session_state["documents_processed"] = vector_store is not None

if "documents_processed" not in st.session_state:
    st.session_state["documents_processed"] = False

if "processing_status" not in st.session_state:
    st.session_state["processing_status"] = ""

if "chat_history" not in st.session_state:
    # Try to load from database
    st.session_state["chat_history"] = get_chat_history()

if "diagrams" not in st.session_state:
    # Try to load from database
    st.session_state["diagrams"] = get_diagrams()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = current_session

# Function to process uploaded PDF files
def process_uploaded_files(uploaded_files):
    if not uploaded_files:
        st.error("Please upload at least one PDF file.")
        return False
    
    # Process the PDF files
    try:
        with st.spinner("Extracting text from PDFs..."):
            st.session_state["processing_status"] = "Starting document extraction..."
            text_chunks = extract_text_from_pdfs(uploaded_files)
            if not text_chunks:
                st.error("Could not extract any text from the uploaded PDFs.")
                return False
            
            st.session_state["processing_status"] = f"Extracted {len(text_chunks)} text chunks from {len(uploaded_files)} documents."
            
            # Save document chunks to database
            try:
                if len(uploaded_files) == 1:
                    # If only one file, save all chunks to it
                    if save_document_chunks(uploaded_files[0].name, text_chunks):
                        st.session_state["processing_status"] += " Saved document chunks to database."
                    else:
                        st.warning("Could not save document chunks to database.")
                else:
                    # Divide chunks among files
                    chunk_size = len(text_chunks) // len(uploaded_files)
                    for i, file in enumerate(uploaded_files):
                        start_idx = i * chunk_size
                        end_idx = start_idx + chunk_size if i < len(uploaded_files) - 1 else len(text_chunks)
                        file_chunks = text_chunks[start_idx:end_idx]
                        save_document_chunks(file.name, file_chunks)
                    st.session_state["processing_status"] += " Saved all document chunks to database."
            except Exception as db_error:
                st.warning(f"Could not save document data: {str(db_error)}")
                # Continue processing even if database saving fails
        
        with st.spinner("Creating vector embeddings... This may take a moment."):
            st.session_state["processing_status"] += " Creating vector embeddings..."
            # Process in smaller batches to avoid memory issues
            max_batch_size = 50  # Process 50 chunks at a time
            all_chunks = []
            
            for i in range(0, len(text_chunks), max_batch_size):
                batch = text_chunks[i:i+max_batch_size]
                st.session_state["processing_status"] = f"Processing batch {i//max_batch_size + 1} of {len(text_chunks)//max_batch_size + 1}..."
                vector_store = create_vector_store(batch)
                if vector_store and "chunks" in vector_store:
                    all_chunks.extend(vector_store["chunks"])
            
            if all_chunks:
                # Set session state for immediate use
                st.session_state["vector_store"] = {
                    "chunks": all_chunks,
                    # Index will be rebuilt when needed
                }
                st.session_state["documents_processed"] = True
                
                # Try to save to database but don't halt if it fails
                try:
                    if save_vector_store(st.session_state["vector_store"]):
                        st.session_state["processing_status"] += " Saved vector store to database."
                    else:
                        st.warning("Could not save vector store to database.")
                except Exception as vs_error:
                    st.warning(f"Vector store saving error: {str(vs_error)}")
                
                st.success("Documents processed successfully!")
                return True
            else:
                st.error("Failed to create vector embeddings.")
                return False
    except Exception as e:
        st.error(f"An error occurred while processing the documents: {str(e)}")
        st.session_state["processing_status"] = f"Error: {str(e)}"
        import traceback
        st.error(traceback.format_exc())
        return False

# Title and description
st.title("Regulatory Document Chatbot")
st.markdown("""
This application allows you to upload regulatory PDF documents and then ask questions about their content.
The chatbot will analyze the documents and provide answers based solely on the information contained within them.
You can also request visual diagrams of concepts and relationships mentioned in the documents.
""")

# Create sidebar for file uploads and processing
with st.sidebar:
    st.header("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload regulatory PDF documents",
        type=["pdf"],
        accept_multiple_files=True
    )
    
    process_button = st.button("Process Documents")
    
    if process_button:
        process_uploaded_files(uploaded_files)
    
    # Display processing status
    if st.session_state["processing_status"]:
        st.info(st.session_state["processing_status"])
    
    # Diagram type selection
    st.header("Diagram Options")
    st.markdown("""
    You can ask for different types of diagrams by including keywords in your question:
    - **Flowchart**: Visualize processes and workflows
    - **Sequence**: Show step-by-step processes or timelines
    - **Mind Map**: Organize related concepts and ideas
    - **Class Diagram**: Show entities and their relationships
    
    Example queries:
    - "Create a flowchart of the compliance process"
    - "Draw a diagram of the data protection framework"
    - "Generate a mind map of key regulatory principles"
    """)
    
    # Session management
    st.header("Session Management")
    
    # Display current session
    st.info(f"Current Session: {datetime.datetime.fromtimestamp(int(st.session_state['session_id'])).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # New session button
    if st.button("Start New Session"):
        new_session_id = create_new_session()
        st.session_state["session_id"] = new_session_id
        st.session_state["vector_store"] = None
        st.session_state["documents_processed"] = False
        st.session_state["processing_status"] = ""
        st.session_state["chat_history"] = []
        st.session_state["diagrams"] = []
        st.success("Started a new session!")
        st.rerun()
    
    # Reset button
    if st.button("Reset Current Session"):
        delete_session(st.session_state["session_id"])
        new_session_id = create_new_session()
        st.session_state["session_id"] = new_session_id
        st.session_state["vector_store"] = None
        st.session_state["documents_processed"] = False
        st.session_state["processing_status"] = ""
        st.session_state["chat_history"] = []
        st.session_state["diagrams"] = []
        st.success("Current session has been reset. You can upload new documents.")
        st.rerun()

# Main chat interface
st.header("Ask Questions About Your Documents")

if not st.session_state["documents_processed"]:
    st.info("Please upload and process documents to start asking questions.")
else:
    # Display chat history
    for i, (question, answer) in enumerate(st.session_state["chat_history"]):
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            st.write(answer)
    
    # Display diagrams (if any)
    if st.session_state["diagrams"]:
        st.header("Generated Diagrams")
        for idx, (diagram_code, explanation, diagram_type) in enumerate(st.session_state["diagrams"]):
            with st.expander(f"Diagram {idx+1}: {explanation[:50]}...", expanded=True):
                st.markdown(f"**Diagram Type**: {diagram_type.capitalize()}")
                st.markdown(f"**Explanation**: {explanation}")
                st.markdown(f"```mermaid\n{diagram_code}\n```")
    
    # Input for new questions
    user_question = st.chat_input("Type your question here or ask for a diagram...")
    
    if user_question:
        # Show user question
        with st.chat_message("user"):
            st.write(user_question)
        
        # Check if this is a diagram request
        is_diagram_request, diagram_type = detect_diagram_request(user_question)
        
        # Display assistant response with typing animation
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Check if we have document data
            if "vector_store" not in st.session_state or not st.session_state["vector_store"]:
                full_response = "I don't have any document data to work with. Please upload and process documents first."
                st.error("No document data is available. Please upload and process documents first.")
            else:
                # Try to find relevant document chunks
                try:
                    with st.status("Finding relevant information in the documents..."):
                        relevant_chunks = get_similar_chunks(user_question, st.session_state["vector_store"])
                    
                    if not relevant_chunks:
                        full_response = "I couldn't find relevant information in the documents to answer your question. Please try rephrasing or ask another question."
                    else:
                        # We have relevant chunks, proceed to generate response
                        if is_diagram_request and diagram_type is not None:
                            # Generate diagram
                            with st.spinner(f"Generating {diagram_type} diagram..."):
                                success, result = generate_diagram(user_question, relevant_chunks, diagram_type)
                                
                                if success and isinstance(result, dict):
                                    # Access dictionary values safely
                                    diagram_code = result.get("diagram_code", "")
                                    explanation = result.get("explanation", "")
                                    
                                    # Store the diagram in session state
                                    st.session_state["diagrams"].append((diagram_code, explanation, diagram_type))
                                    
                                    # Save diagrams to database
                                    try:
                                        save_diagrams(st.session_state["diagrams"])
                                    except Exception as e:
                                        st.warning(f"Could not save diagram to database: {str(e)}")
                                    
                                    full_response = f"I've created a {diagram_type} diagram based on the document content. You can view it in the 'Generated Diagrams' section above. \n\n{explanation}"
                                else:
                                    full_response = f"I couldn't generate a diagram based on your request: {result}"
                        else:
                            # Generate a regular answer for non-diagram questions
                            with st.spinner("Generating answer..."):
                                answer = generate_answer(user_question, relevant_chunks)
                                full_response = answer
                except Exception as e:
                    st.error(f"Error processing your question: {str(e)}")
                    full_response = "I encountered an error when processing your question. Please try again or upload new documents."
            
            # Simulate typing
            response = ""
            for chunk in full_response.split():
                response += chunk + " "
                time.sleep(0.01)
                message_placeholder.write(response)
            
            # Store in chat history (session state)
            st.session_state["chat_history"].append((user_question, full_response))
            
            # Save chat history to database
            try:
                save_chat_history(st.session_state["chat_history"])
            except Exception as e:
                st.warning(f"Could not save chat history to database: {str(e)}")
        
        # Rerun the app to ensure the diagram is displayed immediately
        if is_diagram_request and len(st.session_state["diagrams"]) > 0:
            st.rerun()

# Footer with application information
st.markdown("---")
st.markdown("""
**About this application**:
- Upload regulatory PDF documents to analyze their content
- Ask specific questions about the regulations
- Request visual diagrams to better understand concepts and relationships
- The application will search through the documents and provide accurate answers
- All answers and diagrams are generated based solely on the content of the uploaded documents
- Your data is persistently stored in the Replit Database
""")

# Diagram showing how the application works
st.header("How It Works")
mermaid_diagram = """
```mermaid
graph TD
    A[Upload PDFs] --> B[Extract Text]
    B --> C[Create Vector Embeddings]
    C --> D[Store Document Chunks]
    D --> DB1[(Replit Database)]
    E[User Question] --> F[Find Relevant Chunks]
    F --> G{Is Diagram Request?}
    G -->|Yes| H[Generate Mermaid Diagram]
    G -->|No| I[Generate Text Answer]
    H --> J[Display Diagram]
    J --> DB2[(Replit Database)]
    I --> K[Display Response]
    K --> DB3[(Replit Database)]
```
"""
st.markdown(mermaid_diagram)
