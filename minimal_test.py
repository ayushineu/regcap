import streamlit as st
import os

# Set page configuration
st.set_page_config(
    page_title="Minimal Test App",
    page_icon="📚",
    layout="wide"
)

# Title and description
st.title("Minimal Test App")
st.markdown("""
This is a minimal test application to check if the basic Streamlit functionality is working.
""")

# Display system information
st.header("System Information")

# Check environment variables
if 'OPENAI_API_KEY' in os.environ:
    st.success("✅ OpenAI API key is set")
else:
    st.error("❌ OpenAI API key is not set")

# Check if directories exist
data_storage_exists = os.path.exists('data_storage')
st.write(f"Data storage directory exists: {data_storage_exists}")

# Create a simple form to test user interaction
st.header("Test User Interaction")
with st.form("test_form"):
    input_text = st.text_input("Enter some text")
    submit_button = st.form_submit_button("Submit")

if submit_button:
    st.success(f"You entered: {input_text}")

# Add a simple file uploader
st.header("Test File Upload")
uploaded_file = st.file_uploader("Upload a file", type=["pdf", "txt"])

if uploaded_file is not None:
    st.success(f"Uploaded file: {uploaded_file.name}")
    # Show file details
    file_details = {
        "Filename": uploaded_file.name,
        "File size": uploaded_file.size,
        "File type": uploaded_file.type
    }
    st.json(file_details)

# Footer
st.markdown("---")
st.markdown("Test application to diagnose server issues")