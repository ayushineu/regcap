import streamlit as st
import os
import time
import json
import base64
import pickle
import traceback
from openai import OpenAI

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None

# Set page configuration
st.set_page_config(
    page_title="Diagnostic Test App",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if "test_results" not in st.session_state:
    st.session_state["test_results"] = []

if "diagnostic_phase" not in st.session_state:
    st.session_state["diagnostic_phase"] = 0

# Title and description
st.title("Regulatory Document Chatbot - Diagnostic Mode")
st.markdown("""
This is a diagnostic version of the application that tests each component separately to identify issues.
""")

# Create status container
status_container = st.empty()

# Feature test functions
def test_file_storage():
    """Test the file-based storage system"""
    try:
        # Create storage directory
        os.makedirs("data_storage", exist_ok=True)
        
        # Create a test object
        test_data = {
            "timestamp": time.time(),
            "test_value": "This is a test"
        }
        
        # Save to file
        with open("data_storage/test_file.json", "w") as f:
            json.dump(test_data, f)
        
        # Read back
        with open("data_storage/test_file.json", "r") as f:
            read_data = json.load(f)
        
        # Verify
        if read_data["test_value"] == test_data["test_value"]:
            return True, "File storage system is working correctly"
        else:
            return False, "Data verification failed"
    except Exception as e:
        return False, f"File storage test failed: {str(e)}\n{traceback.format_exc()}"

def test_data_serialization():
    """Test pickle serialization and base64 encoding"""
    try:
        # Create a complex object
        test_obj = {
            "numeric_array": [1, 2, 3, 4, 5],
            "nested": {
                "text": "This is a test",
                "boolean": True
            }
        }
        
        # Serialize
        pickled = pickle.dumps(test_obj)
        encoded = base64.b64encode(pickled).decode('utf-8')
        
        # Deserialize
        decoded_bytes = base64.b64decode(encoded.encode('utf-8'))
        unpickled = pickle.loads(decoded_bytes)
        
        # Verify
        if unpickled["nested"]["text"] == test_obj["nested"]["text"]:
            return True, "Data serialization is working correctly"
        else:
            return False, "Serialization verification failed"
    except Exception as e:
        return False, f"Serialization test failed: {str(e)}\n{traceback.format_exc()}"

def test_openai_connection():
    """Test OpenAI API connection"""
    try:
        if not client:
            return False, "OpenAI API key is not configured"
        
        # Make a simple API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'Connection successful' in one sentence"}],
            max_tokens=20
        )
        
        result_text = response.choices[0].message.content
        
        return True, f"OpenAI API connection successful. Response: '{result_text}'"
    except Exception as e:
        return False, f"OpenAI API test failed: {str(e)}\n{traceback.format_exc()}"

def test_simple_pdf_handling():
    """Test basic PDF file handling (without content extraction)"""
    try:
        # Create a test file
        with open("data_storage/test_file.txt", "w") as f:
            f.write("This is a test file.\nIt has multiple lines.\nIt will be used to simulate PDF processing.")
        
        # Read the file
        with open("data_storage/test_file.txt", "r") as f:
            content = f.read()
        
        # Split into chunks
        chunks = [content[i:i+100] for i in range(0, len(content), 100)]
        
        return True, f"Basic file processing successful. Created {len(chunks)} chunks from the test file."
    except Exception as e:
        return False, f"File handling test failed: {str(e)}\n{traceback.format_exc()}"

# Sidebar with test controls
with st.sidebar:
    st.header("Diagnostic Controls")
    
    # Run all tests button
    if st.button("Run All Tests"):
        st.session_state["test_results"] = []
        
        # Test 1: File Storage
        status_container.info("Testing file storage...")
        success, message = test_file_storage()
        st.session_state["test_results"].append(("File Storage", success, message))
        
        # Test 2: Data Serialization
        status_container.info("Testing data serialization...")
        success, message = test_data_serialization()
        st.session_state["test_results"].append(("Data Serialization", success, message))
        
        # Test 3: OpenAI API
        status_container.info("Testing OpenAI API connection...")
        success, message = test_openai_connection()
        st.session_state["test_results"].append(("OpenAI API", success, message))
        
        # Test 4: PDF Handling
        status_container.info("Testing basic file handling...")
        success, message = test_simple_pdf_handling()
        st.session_state["test_results"].append(("Basic File Handling", success, message))
        
        status_container.success("All tests completed!")

    # Test file uploader
    st.header("Test File Upload")
    uploaded_file = st.file_uploader("Upload a test file", type=["pdf", "txt"])
    
    if uploaded_file is not None:
        st.success(f"Successfully uploaded: {uploaded_file.name}")
        # Show file details
        file_details = {
            "Filename": uploaded_file.name,
            "File size": uploaded_file.size,
            "File type": uploaded_file.type
        }
        st.json(file_details)
        
        # Save uploaded file for testing
        if st.button("Save File for Testing"):
            with open(f"data_storage/{uploaded_file.name}", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved {uploaded_file.name} to data_storage directory")

# Display test results
st.header("Diagnostic Test Results")
if st.session_state["test_results"]:
    for name, success, message in st.session_state["test_results"]:
        if success:
            st.success(f"✅ {name}: {message}")
        else:
            st.error(f"❌ {name}: {message}")
            with st.expander("Error Details"):
                st.code(message)
else:
    st.info("No tests have been run yet. Use the controls in the sidebar to run tests.")

# Advanced diagnostic tools
st.header("Advanced Diagnostics")

# Environment variables
with st.expander("Environment Variables"):
    st.code("\n".join([f"{key}={('[REDACTED]' if 'KEY' in key or 'SECRET' in key else value)}" 
                      for key, value in os.environ.items()]))

# System information
with st.expander("Directory Structure"):
    st.code(os.popen("find . -type f -not -path '*/\\.*' | sort").read())

# Footer
st.markdown("---")
st.caption("Diagnostic app for troubleshooting the Regulatory Document Chatbot")