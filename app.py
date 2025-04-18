"""
RegCap GPT - Regulatory Intelligence Platform

A ChatGPT-style interface for regulatory document analysis using AI.
"""

import streamlit as st
import time
import os

# Set custom theme and page configuration
st.set_page_config(
    page_title="RegCap GPT - Regulatory Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ChatGPT-style UI
st.markdown("""
<style>
    /* Main color scheme */
    :root {
        --primary-color: #0088cc;
        --primary-color-hover: #006699;
        --background-color: #f8f9fa;
        --text-color: #212529;
        --secondary-bg: #ffffff;
        --border-color: #dee2e6;
    }
    
    /* Dark mode class */
    .dark-mode {
        --background-color: #1a1a1a;
        --text-color: #f8f9fa;
        --secondary-bg: #2d2d2d;
        --border-color: #444444;
    }
    
    /* Base styles */
    .main {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    /* Header styling */
    h1, h2, h3 {
        color: #0088cc !important;
    }
    
    /* Top Banner */
    .top-banner {
        background-color: #0088cc;
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Chat container */
    .chat-container {
        background-color: var(--secondary-bg);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid var(--border-color);
    }
    
    /* Chat message styles */
    .user-message {
        background-color: #e6f3ff;
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        margin-left: auto;
        border: 1px solid #cce5ff;
    }
    
    .assistant-message {
        background-color: #f1f3f5;
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        border: 1px solid #dee2e6;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #0088cc;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
    }
    
    .stButton > button:hover {
        background-color: #006699;
    }
    
    /* Input field styling */
    .stTextArea > div > div > textarea {
        border-radius: 5px;
        border: 1px solid var(--border-color);
    }
    
    /* Nav button styles */
    .nav-buttons {
        display: flex;
        gap: 5px;
        margin-bottom: 20px;
    }
    
    .nav-button {
        background-color: transparent;
        color: #0088cc;
        border: 1px solid #0088cc;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .nav-button:hover {
        background-color: #0088cc;
        color: white;
    }
    
    .nav-button.active {
        background-color: #0088cc;
        color: white;
    }
    
    /* Hide default radio button */
    div.st-cc {
        display: none;
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Dark mode toggle button */
    .dark-mode-toggle {
        position: absolute;
        top: 10px;
        left: 10px;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# Add a dark mode toggle button in top-left corner
col1, col2, col3 = st.columns([1, 10, 1])
with col1:
    dark_mode = st.checkbox("🌓", value=False, key="dark_mode")
    if dark_mode:
        st.markdown("""
        <script>
            document.body.classList.add('dark-mode');
        </script>
        """, unsafe_allow_html=True)

# Top banner across the full screen
st.markdown("""
<div class="top-banner">
    <div>
        <h1 style="margin:0; color: white !important; font-size: 28px;">RegCap GPT</h1>
        <p style="margin:0;">Regulatory Intelligence</p>
    </div>
    <div>
        <p>🚧 Beta: Features may be limited or evolving.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Create custom navigation buttons
st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
option = st.radio(
    "Navigation",
    ["💬 Chat", "📄 Documents", "📊 Diagrams", "⚙️ Sessions"],
    label_visibility="collapsed",
    horizontal=True
)
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar with additional information
with st.sidebar:
    # About section
    st.subheader("About RegCap GPT")
    st.write("""
    RegCap GPT helps you understand complex regulatory documents through AI-powered analysis, question answering, and visualization.
    """)
    
    # Version info
    st.caption("Version 1.0.0")

# Main content area based on selected option
if "💬 Chat" in option:
    st.header("Chat with RegCap GPT")
    
    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Example chat messages
    st.markdown('<div class="user-message">How does the ISO 20022 message standard work?</div>', unsafe_allow_html=True)
    
    st.markdown("""<div class="assistant-message">
    ISO 20022 is a global standard for financial messaging that provides:
    
    1. A common language for financial institutions worldwide
    2. Standardized message formats for payments, securities, trade, and cards
    3. Rich, structured data with detailed information about transactions
    4. Support for both traditional and modern payment systems
    
    The standard uses XML schema and has a layered structure with business processes, message flows, and detailed message definitions. This enables more efficient processing, better regulatory compliance, and enhanced interoperability across different financial systems.
    </div>""", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Question input
    question = st.text_area("Ask a question about your regulatory documents:", height=100)
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Submit", key="chat_submit"):
            with st.spinner("Processing your question..."):
                time.sleep(1)  # Simulate processing
                st.info("This would call the AI to process your question in the full version.")

elif "📄 Documents" in option:
    st.header("Document Management")
    
    # Upload section
    st.subheader("Upload Documents")
    uploaded_files = st.file_uploader("Upload regulatory documents (PDF)", type=["pdf"], accept_multiple_files=True)
    
    # Sample document list
    st.subheader("Uploaded Documents")
    if not uploaded_files:
        st.info("No documents uploaded yet. Upload PDFs to get started.")
    else:
        for i, file in enumerate(uploaded_files):
            st.write(f"{i+1}. {file.name} ({file.size/1000:.1f} KB)")

elif "📊 Diagrams" in option:
    st.header("Regulatory Visualizations")
    
    # Example diagram
    st.subheader("ISO 20022 Implementation Process")
    st.markdown("""
    ```mermaid
    graph TD
        A[Start Implementation] --> B{Assess Current System}
        B --> C[Define Requirements]
        C --> D[Design Message Flows]
        D --> E[Develop/Test Solutions]
        E --> F[Validate Against Standard]
        F --> G{Compliance Check}
        G -->|Pass| H[Deploy to Production]
        G -->|Fail| E
        H --> I[Monitor & Maintain]
        
        style A fill:#0088cc,color:white
        style H fill:#0088cc,color:white
    ```
    """)
    
    # Explanation
    st.markdown("""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 5px solid #0088cc;">
    <h4 style="color: #0088cc; margin-top: 0;">Diagram Explanation</h4>
    <p>This flowchart illustrates the implementation process for ISO 20022 in a financial institution. It begins with an assessment of current systems, followed by requirement definition, message flow design, development and testing, validation against the standard, and finally deployment after passing compliance checks.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate new diagram section
    st.subheader("Generate New Diagram")
    diagram_query = st.text_area("Describe what visualization you need:", 
                               placeholder="e.g., Show me the flow of a cross-border payment using ISO 20022")
    diagram_type = st.selectbox("Diagram Type", ["Flowchart", "Sequence Diagram", "Class Diagram", "Entity Relationship"])
    
    if st.button("Generate Diagram", key="generate_diagram"):
        with st.spinner("Creating your diagram..."):
            time.sleep(1)  # Simulate processing
            st.info("In the full version, this would generate a custom diagram based on your requirements.")

elif "⚙️ Sessions" in option:
    st.header("Session Management")
    
    # Current session info
    current_session = f"session_{int(time.time())}"
    st.subheader("Current Session")
    st.markdown(f"""
    <div style="background-color: #e6f3ff; padding: 15px; border-radius: 5px; border: 1px solid #cce5ff;">
    <h4 style="margin-top: 0; color: #0088cc;">Active Session: {current_session}</h4>
    <p>Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}</p>
    <p>Documents: 2 uploaded</p>
    <p>Conversations: 5 questions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Session controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create New Session"):
            st.success(f"New session created: session_{int(time.time())+100}")
    with col2:
        if st.button("Export Session Data"):
            st.info("In the full version, this would export all session data as a ZIP file.")
    
    # Available sessions
    st.subheader("Available Sessions")
    sessions = {
        f"session_{int(time.time())}": "Current (Apr 18, 2025)",
        f"session_{int(time.time())-86400}": "Apr 17, 2025",
        f"session_{int(time.time())-172800}": "Apr 16, 2025"
    }
    
    for session, date in sessions.items():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{session}** ({date})")
        with col2:
            if st.button("Load", key=f"load_{session}"):
                st.success(f"Switched to session {session}")
        with col3:
            if st.button("Delete", key=f"delete_{session}"):
                st.error(f"Session {session} deleted")

# Footer
st.markdown("---")
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center;">
    <span>RegCap GPT © 2025</span>
    <span>Powered by Regulatory Intelligence</span>
</div>
""", unsafe_allow_html=True)