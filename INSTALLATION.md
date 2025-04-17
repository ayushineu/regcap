# Installation Guide for RegCap GPT

## System Requirements

- Python 3.10 or higher
- pip package manager
- 4GB RAM minimum (8GB recommended)
- 1GB free disk space

## Required Python Packages

The application depends on the following Python packages:

```
flask==2.3.3
openai==1.3.3
numpy==1.24.3
faiss-cpu==1.7.4
PyPDF2==3.0.1
Werkzeug==2.3.7
```

## Environment Setup

### Using Replit

If you're using Replit, all dependencies should be automatically configured for you through the system configuration.

### Manual Installation

1. **Create and activate a virtual environment (optional but recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

2. **Install the required packages**

   ```bash
   # Using packager_tool on Replit
   # This is handled automatically

   # Using pip on other systems
   pip install flask==2.3.3 openai==1.3.3 numpy==1.24.3 faiss-cpu==1.7.4 PyPDF2==3.0.1 Werkzeug==2.3.7
   ```

## API Key Configuration

The application requires an OpenAI API key to function:

1. **Obtain an API key** from [OpenAI's platform](https://platform.openai.com/)

2. **Set the environment variable**:

   ```bash
   # Linux/macOS:
   export OPENAI_API_KEY='your-api-key-here'
   
   # Windows Command Prompt:
   set OPENAI_API_KEY=your-api-key-here
   
   # Windows PowerShell:
   $env:OPENAI_API_KEY='your-api-key-here'
   ```

   Or on Replit, add it to the Secrets manager in the project settings.

## Verifying Installation

After setting up, you can verify your installation by running:

```bash
python simplified_app.py
```

The application should start without errors and be accessible at http://localhost:5000.