import streamlit as st
import os
import time
from utils.pdf_processor import extract_text_from_pdfs
from utils.vector_store import create_vector_store, get_similar_chunks
from utils.openai_helper import generate_answer, generate_diagram, detect_diagram_request

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
if "diagrams" not in st.session_state:
    st.session_state["diagrams"] = []

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
        
    # Reset button
    if st.button("Reset"):
        st.session_state["vector_store"] = None
        st.session_state["documents_processed"] = False
        st.session_state["processing_status"] = ""
        st.session_state["chat_history"] = []
        st.session_state["diagrams"] = []
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
            
            # Get similar chunks from the vector store
            relevant_chunks = get_similar_chunks(user_question, st.session_state["vector_store"])
            
            if not relevant_chunks:
                full_response = "I couldn't find relevant information in the documents to answer your question. Please try rephrasing or ask another question."
            else:
                # If it's a diagram request, generate a diagram
                if is_diagram_request:
                    with st.spinner(f"Generating {diagram_type} diagram..."):
                        success, result = generate_diagram(user_question, relevant_chunks, diagram_type)
                        
                        if success:
                            diagram_code = result["diagram_code"]
                            explanation = result["explanation"]
                            
                            # Store the diagram
                            st.session_state["diagrams"].append((diagram_code, explanation, diagram_type))
                            
                            full_response = f"I've created a {diagram_type} diagram based on the document content. You can view it in the 'Generated Diagrams' section above. \n\n{explanation}"
                        else:
                            full_response = f"I couldn't generate a diagram based on your request: {result}"
                else:
                    # Generate a regular answer for non-diagram questions
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
    F --> G{Is Diagram Request?}
    G -->|Yes| H[Generate Mermaid Diagram]
    G -->|No| I[Generate Text Answer]
    H --> J[Display Diagram]
    I --> K[Display Response]
```
"""
st.markdown(mermaid_diagram)
