import streamlit as st
import os
import time
from utils.pdf_processor import extract_text_from_pdfs
from utils.vector_store import create_vector_store, get_similar_chunks
from utils.openai_helper import generate_answer

# Set page configuration
st.set_page_config(
    page_title="Regulatory Document Chatbot",
    page_icon="📚",
    layout="wide"
)

# Initialize session state variables
if "vector_store" not in st.session_state:
    st.session_state["vector_store"] = None
if "documents_processed" not in st.session_state:
    st.session_state["documents_processed"] = False
if "processing_status" not in st.session_state:
    st.session_state["processing_status"] = ""
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Function to process uploaded PDF files
def process_uploaded_files(uploaded_files):
    if not uploaded_files:
        st.error("Please upload at least one PDF file.")
        return False
    
    # Process the PDF files
    try:
        with st.spinner("Extracting text from PDFs..."):
            text_chunks = extract_text_from_pdfs(uploaded_files)
            if not text_chunks:
                st.error("Could not extract any text from the uploaded PDFs.")
                return False
            
            st.session_state["processing_status"] = f"Extracted {len(text_chunks)} text chunks from {len(uploaded_files)} documents."
        
        with st.spinner("Creating vector embeddings... This may take a moment."):
            vector_store = create_vector_store(text_chunks)
            if vector_store:
                st.session_state["vector_store"] = vector_store
                st.session_state["documents_processed"] = True
                st.success("Documents processed successfully!")
                return True
            else:
                st.error("Failed to create vector embeddings.")
                return False
    except Exception as e:
        st.error(f"An error occurred while processing the documents: {str(e)}")
        return False

# Title and description
st.title("Regulatory Document Chatbot")
st.markdown("""
This application allows you to upload regulatory PDF documents and then ask questions about their content.
The chatbot will analyze the documents and provide answers based solely on the information contained within them.
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
        
    # Reset button
    if st.button("Reset"):
        st.session_state["vector_store"] = None
        st.session_state["documents_processed"] = False
        st.session_state["processing_status"] = ""
        st.session_state["chat_history"] = []
        st.success("Application has been reset. You can upload new documents.")
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
    
    # Input for new questions
    user_question = st.chat_input("Type your question here...")
    
    if user_question:
        # Show user question
        with st.chat_message("user"):
            st.write(user_question)
        
        # Display assistant response with typing animation
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Get similar chunks from the vector store
            relevant_chunks = get_similar_chunks(user_question, st.session_state["vector_store"])
            
            if not relevant_chunks:
                full_response = "I couldn't find relevant information in the documents to answer your question. Please try rephrasing or ask another question."
            else:
                # Generate answer based on the relevant chunks
                with st.spinner("Generating answer..."):
                    answer = generate_answer(user_question, relevant_chunks)
                    full_response = answer
            
            # Simulate typing
            response = ""
            for chunk in full_response.split():
                response += chunk + " "
                time.sleep(0.01)
                message_placeholder.write(response)
            
            # Store in chat history
            st.session_state["chat_history"].append((user_question, full_response))

# Footer with application information
st.markdown("---")
st.markdown("""
**About this application**:
- Upload regulatory PDF documents to analyze their content
- Ask specific questions about the regulations
- The application will search through the documents and provide accurate answers
- All answers are generated based solely on the content of the uploaded documents
""")

# Diagram showing how the application works
st.header("How It Works")
mermaid_diagram = """
```mermaid
graph TD
    A[Upload PDFs] --> B[Extract Text]
    B --> C[Create Vector Embeddings]
    C --> D[Store Document Chunks]
    E[User Question] --> F[Find Relevant Chunks]
    F --> G[Generate Answer with OpenAI]
    G --> H[Display Response]
```
"""
st.markdown(mermaid_diagram)
