# RegCap GPT - AI-Powered Regulatory Intelligence Assistant

## Overview

RegCap GPT is a Flask-based web application that serves as an AI-powered regulatory intelligence assistant. The application enables users to upload PDF regulatory documents, ask natural language questions about their content, and receive AI-generated answers along with visual diagrams. It leverages OpenAI's GPT-4o for intelligent responses, vector-based semantic search using FAISS for document retrieval, and Mermaid.js for diagram generation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular Flask architecture with a single-page application frontend and RESTful API endpoints. The system is designed for deployment on Replit and uses file-based storage for persistence.

### Core Components
- **Flask Web Framework**: Main application server handling HTTP requests and responses
- **Frontend**: Single-page HTML application with Bootstrap UI and JavaScript for dynamic interactions
- **Vector Search Engine**: FAISS-based semantic search with OpenAI embeddings
- **Document Processing**: PyPDF2 for text extraction from regulatory PDFs
- **AI Integration**: OpenAI GPT-4o for question answering and content generation
- **Diagram Generation**: Mermaid.js for creating flowcharts and process diagrams

## Key Components

### Backend Architecture
- **app.py**: Main Flask application with all routes and business logic
- **utils/**: Utility modules for specialized functionality
  - **pdf_processor.py**: PDF text extraction and chunking
  - **vector_store.py**: FAISS vector store management and embedding generation
  - **openai_helper.py**: OpenAI API integration for answers and embeddings
  - **db_manager.py**: Simple file-based storage manager
- **fix_mermaid.py**: Mermaid diagram syntax validation and correction

### Frontend Architecture
- **Single HTML Template**: Embedded in Flask app with multi-tab interface
- **Bootstrap 5**: Responsive UI framework
- **JavaScript**: Dynamic interactions, AJAX calls, and real-time updates
- **Mermaid.js**: Client-side diagram rendering

### Data Storage
- **File-based Storage**: JSON files in `data_storage/` directory
- **Session Management**: Multiple conversation contexts with document isolation
- **Vector Indices**: FAISS indices stored as binary files
- **Document Storage**: Uploaded PDFs processed and stored as text chunks

## Data Flow

### Document Upload and Processing
1. User uploads PDF files through web interface
2. PyPDF2 extracts text content page by page
3. Text is chunked into semantic segments with metadata
4. OpenAI generates embeddings for each chunk
5. FAISS vector index is created and stored
6. Document metadata is saved to session storage

### Question Answering Process
1. User submits natural language question
2. Question is converted to embedding using OpenAI
3. FAISS performs semantic search to find relevant chunks
4. Top relevant chunks are passed to GPT-4o as context
5. AI generates answer based on document content
6. Response includes source attribution and citations

### Diagram Generation
1. System detects requests for visual explanations
2. GPT-4o generates Mermaid.js diagram code
3. Syntax validation and correction applied
4. Diagram rendered in dedicated tab with explanations

## External Dependencies

### Core Python Libraries
- **Flask 2.3.3**: Web framework
- **OpenAI 1.3.3**: AI model integration
- **PyPDF2 3.0.1**: PDF text extraction
- **NumPy 1.24.3**: Numerical computations for embeddings
- **FAISS-CPU 1.7.4**: Vector similarity search
- **Werkzeug 2.3.7**: WSGI utilities

### Frontend Libraries (CDN)
- **Bootstrap 5.3.0**: CSS framework
- **Font Awesome 4.7.0**: Icons
- **Mermaid.js 8.14.0**: Diagram rendering

### External Services
- **OpenAI API**: GPT-4o for text generation and text-embedding-ada-002 for embeddings
- **Requires OPENAI_API_KEY environment variable**

## Deployment Strategy

The application is configured for Replit deployment with multiple entry points to ensure compatibility:

### Deployment Files
- **deployment.py**: Primary deployment entry point
- **main.py**: Alternative entry point for standard deployments
- **wsgi.py**: WSGI-compatible entry point for production servers
- **simple_deploy.py**: Streamlined deployment script with fallback handling

### Environment Configuration
- **Host**: 0.0.0.0 (accepts connections from any IP)
- **Port**: 5000 (configurable via PORT environment variable)
- **Storage**: File-based persistence in `data_storage/` directory
- **Session Management**: Flask sessions with file-based backend

### Error Handling and Resilience
- Graceful degradation when optional dependencies unavailable
- Fallback Flask app if main application import fails
- Comprehensive error logging and status endpoints
- Multiple deployment entry points for different hosting scenarios

The application is designed to be stateless at the application level while maintaining user sessions through file-based storage, making it suitable for containerized deployment environments.