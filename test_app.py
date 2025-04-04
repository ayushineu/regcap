import streamlit as st
import time

# Set page configuration
st.set_page_config(
    page_title="Regulatory Document Chatbot Test",
    page_icon="📚",
    layout="wide"
)

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Title and description
st.title("Regulatory Document Chatbot Test")
st.markdown("""
This is a simplified version of the app to diagnose issues.
""")

# Create sidebar
with st.sidebar:
    st.header("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload regulatory PDF documents",
        type=["pdf"],
        accept_multiple_files=True
    )
    
    process_button = st.button("Process Documents")
    
    if process_button:
        st.success("Test processing complete!")

# Main chat interface
st.header("Ask Questions About Your Documents")

# Input for new questions
user_question = st.chat_input("Type your question here...")

if user_question:
    # Show user question
    with st.chat_message("user"):
        st.write(user_question)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = "This is a test response. The app is working correctly."
        
        # Simulate typing
        response = ""
        for chunk in full_response.split():
            response += chunk + " "
            time.sleep(0.05)
            message_placeholder.write(response)
        
        # Store in chat history
        st.session_state["chat_history"].append((user_question, full_response))

# Display chat history
for question, answer in st.session_state["chat_history"]:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        st.write(answer)

# Footer
st.markdown("---")
st.markdown("**Test App**")