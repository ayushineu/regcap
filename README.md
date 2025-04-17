# RegCap GPT

A regulatory intelligence platform that transforms complex PDF content into actionable insights using AI and visualizations. RegCap GPT enables users to upload regulatory documents and ask natural language questions to gain understanding and visualize key concepts.

## Features

- **PDF Document Processing**: Upload regulatory PDFs and extract content efficiently
- **Natural Language Q&A**: Ask questions about regulatory documents in plain English
- **Interactive Visualizations**: Generate flowcharts, sequence diagrams, and other visualizations to explain complex regulatory concepts
- **Multi-Session Management**: Create and switch between different contexts for organized research
- **Dark/Light Theme**: Built-in theme switching for comfortable viewing in any environment
- **Document Management**: Track uploaded documents and their contents
- **Efficient Vector Search**: Utilizes FAISS for fast, accurate semantic search of document content

## Tech Stack

- **Frontend**: Flask with Bootstrap for responsive UI
- **Backend**: Python 3.10+
- **AI Language Model**: OpenAI GPT models
- **Document Processing**: PyPDF2
- **Vector Database**: FAISS for efficient similarity search
- **Diagram Generation**: Mermaid.js for rendering visualizations
- **Data Persistence**: Simple file-based storage system with serialization

## Getting Started

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/regcap-gpt.git
   cd regcap-gpt
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY='your_api_key_here'
   ```

### Running the Application

1. Start the Flask server:
   ```
   python simplified_app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. **Upload Documents**: Click on the "Documents" tab and upload regulatory PDFs
2. **Ask Questions**: Return to the "Chat" tab and type your question in the input field
3. **View Diagrams**: When you ask for visualizations, they'll appear in the "Diagrams" tab
4. **Manage Sessions**: Use the "Sessions" tab to create new research contexts or switch between existing ones

## Requesting Diagrams

To generate visualizations, include phrases like these in your questions:
- "Create a flowchart of..."
- "Show me a diagram of..."
- "Visualize the process for..."
- "Can you make a diagram explaining..."

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for providing the language models
- Mermaid.js for the diagram rendering capabilities
- FAISS for the vector search implementation
