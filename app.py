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
        # Create a status message to track progress
        status_container = st.empty()
        status_container.info("Starting document processing...")
        st.session_state["processing_status"] = "Starting document extraction..."
        
        # Step 1: Extract text from PDFs with robust error handling
        extracted_text_chunks = []
        successful_files = []
        
        for i, file in enumerate(uploaded_files):
            try:
                status_container.info(f"Processing file {i+1}/{len(uploaded_files)}: {file.name}")
                st.session_state["processing_status"] = f"Extracting text from {file.name}..."
                
                # Process one file at a time to prevent memory issues
                file_chunks = extract_text_from_pdfs([file])
                
                if file_chunks:
                    extracted_text_chunks.extend(file_chunks)
                    successful_files.append(file)
                    status_container.success(f"Successfully extracted {len(file_chunks)} chunks from {file.name}")
                else:
                    status_container.warning(f"No text could be extracted from {file.name}")
            except Exception as extract_error:
                status_container.error(f"Error extracting text from {file.name}: {str(extract_error)}")
                # Continue with next file
        
        if not extracted_text_chunks:
            status_container.error("Could not extract any text from the uploaded PDFs.")
            st.session_state["processing_status"] = "Failed to extract any text from documents."
            return False
        
        total_chunks = len(extracted_text_chunks)
        status_container.success(f"Successfully extracted {total_chunks} text chunks from {len(successful_files)} documents.")
        st.session_state["processing_status"] = f"Extracted {total_chunks} chunks from {len(successful_files)} documents."
        
        # Step 2: Save document chunks to database (file by file)
        try:
            for file in successful_files:
                # Find chunks for this file
                file_index = uploaded_files.index(file)
                chunk_size = max(1, total_chunks // len(successful_files))
                start_idx = file_index * chunk_size
                end_idx = start_idx + chunk_size if file_index < len(successful_files) - 1 else total_chunks
                file_chunks = extracted_text_chunks[start_idx:end_idx]
                
                # Try to save these chunks
                try:
                    save_document_chunks(file.name, file_chunks)
                    status_container.info(f"Saved chunks for {file.name}")
                except Exception as file_save_error:
                    status_container.warning(f"Could not save chunks for {file.name}: {str(file_save_error)}")
                
            st.session_state["processing_status"] += " Saved available document chunks."
        except Exception as db_error:
            status_container.warning(f"Issues saving document data: {str(db_error)}")
            # Continue processing even if database saving fails
        
        # Step 3: Create vector embeddings with very small batches to avoid memory issues
        status_container.info("Creating vector embeddings... This may take a moment.")
        st.session_state["processing_status"] += " Creating vector embeddings..."
        
        # Use a much smaller batch size to handle very large documents
        max_batch_size = 5  # Extremely reduced batch size to avoid memory issues
        all_processed_chunks = []
        total_batches = (total_chunks - 1) // max_batch_size + 1
        
        for i in range(0, total_chunks, max_batch_size):
            batch = extracted_text_chunks[i:i+max_batch_size]
            batch_num = i // max_batch_size + 1
            
            status_container.info(f"Processing batch {batch_num} of {total_batches}...")
            st.session_state["processing_status"] = f"Processing batch {batch_num}/{total_batches}..."
            
            try:
                # Create formatted chunks with content and metadata
                formatted_chunks = []
                for j, chunk in enumerate(batch):
                    try:
                        # Skip empty chunks
                        if not chunk.strip():
                            continue
                            
                        # Create a properly formatted chunk
                        formatted_chunks.append({
                            "content": chunk,
                            "metadata": {
                                "chunk_id": f"{i+j}",
                                "batch": batch_num,
                                "document": successful_files[min(i//chunk_size, len(successful_files)-1)].name
                            }
                        })
                    except Exception as chunk_format_error:
                        status_container.warning(f"Error formatting chunk {i+j}: {str(chunk_format_error)}")
                
                # Only process if we have valid chunks
                if formatted_chunks:
                    try:
                        vector_store = create_vector_store(formatted_chunks)
                        if vector_store and "chunks" in vector_store:
                            all_processed_chunks.extend(vector_store["chunks"])
                            status_container.success(f"Processed batch {batch_num} successfully")
                        else:
                            status_container.warning(f"Batch {batch_num} processing returned no chunks")
                    except Exception as create_error:
                        status_container.error(f"Error processing batch {batch_num}: {str(create_error)}")
                else:
                    status_container.warning(f"No valid chunks in batch {batch_num}")
            except Exception as batch_error:
                status_container.error(f"Error with batch {batch_num}: {str(batch_error)}")
                # Continue with the next batch
        
        # Step 4: Save results if we have any processed chunks
        if all_processed_chunks:
            # Set session state for immediate use
            st.session_state["vector_store"] = {
                "chunks": all_processed_chunks,
                # Index will be rebuilt when needed
            }
            st.session_state["documents_processed"] = True
            
            # Try to save to database but don't halt if it fails
            try:
                if save_vector_store(st.session_state["vector_store"]):
                    status_container.success("Saved vector store to database")
                    st.session_state["processing_status"] += " Saved vector store to database."
                else:
                    status_container.warning("Could not save vector store to database, but documents are still available for this session")
            except Exception as vs_error:
                status_container.warning(f"Vector store saving error: {str(vs_error)}")
                st.session_state["processing_status"] += " (Note: Vector store could not be saved to database but is available for this session)"
            
            status_container.success(f"Documents processed successfully! Processed {len(all_processed_chunks)} chunks.")
            return True
        else:
            status_container.error("Failed to create vector embeddings for any chunk. Try uploading smaller or different PDF files.")
            st.session_state["processing_status"] = "Failed to create any vector embeddings."
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
                                # Handle None value for diagram_type by defaulting to flowchart
                                diagram_type_str = diagram_type if diagram_type is not None else "flowchart"
                                success, result = generate_diagram(user_question, relevant_chunks, diagram_type_str)
                                
                                if success and isinstance(result, dict):
                                    # Access dictionary values safely
                                    diagram_code = result.get("diagram_code", "")
                                    explanation = result.get("explanation", "")
                                    
                                    # Store the diagram in session state
                                    st.session_state["diagrams"].append((diagram_code, explanation, diagram_type_str))
                                    
                                    # Save diagrams to database
                                    try:
                                        save_diagrams(st.session_state["diagrams"])
                                    except Exception as e:
                                        st.warning(f"Could not save diagram to database: {str(e)}")
                                    
                                    full_response = f"I've created a {diagram_type_str} diagram based on the document content. You can view it in the 'Generated Diagrams' section above. \n\n{explanation}"
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
