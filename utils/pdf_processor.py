import io
import PyPDF2
import streamlit as st

def extract_text_from_pdf(file):
    """
    Extract text from a single PDF file using PyPDF2.
    
    Args:
        file: A file-like object containing the PDF
        
    Returns:
        A list of text chunks from the document
    """
    try:
        file_stream = io.BytesIO(file.getvalue())
        reader = PyPDF2.PdfReader(file_stream)
        
        text_chunks = []
        
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            
            # Skip empty pages
            if not text or not text.strip():
                continue
                
            # Add page number metadata
            page_info = f"Document: {file.name}, Page: {page_num + 1}"
            chunk = {
                "content": text,
                "metadata": {
                    "source": file.name,
                    "page": page_num + 1
                }
            }
            text_chunks.append(chunk)
            
        return text_chunks
    
    except Exception as e:
        print(f"Error processing PDF {file.name}: {str(e)}")
        if hasattr(st, 'error'):  # Check if streamlit is available (for Flask compatibility)
            st.error(f"Error processing PDF {file.name}: {str(e)}")
        return []

def split_text_into_chunks(text, max_chunk_size=1000, overlap=100):
    """
    Split a large text into smaller chunks with overlap.
    
    Args:
        text: The text to split
        max_chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        A list of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        
        # Try to find a natural breakpoint (newline or period)
        if end < len(text):
            # Look for paragraph break
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break > start + max_chunk_size // 2:
                end = paragraph_break + 2
            else:
                # Look for sentence break
                sentence_break = text.rfind('. ', start, end)
                if sentence_break > start + max_chunk_size // 2:
                    end = sentence_break + 2
        
        chunks.append(text[start:end])
        start = end - overlap  # Create overlap with previous chunk
    
    return chunks

def extract_text_from_pdfs(uploaded_files):
    """
    Process multiple PDF files and extract text chunks from them.
    
    Args:
        uploaded_files: List of uploaded PDF files
        
    Returns:
        A list of text chunks from all documents
    """
    all_chunks = []
    
    for file in uploaded_files:
        # Extract basic text from PDF
        pdf_chunks = extract_text_from_pdf(file)
        
        # Further process each chunk to get smaller, overlapping pieces for better context
        processed_chunks = []
        for chunk in pdf_chunks:
            text = chunk["content"]
            metadata = chunk["metadata"]
            
            # Split large chunks into smaller pieces with overlap
            if len(text) > 1000:  # Only split if chunk is large
                smaller_chunks = split_text_into_chunks(text)
                for i, small_chunk in enumerate(smaller_chunks):
                    processed_chunks.append({
                        "content": small_chunk,
                        "metadata": {
                            **metadata,
                            "chunk": i+1,
                            "total_chunks": len(smaller_chunks)
                        }
                    })
            else:
                processed_chunks.append(chunk)
        
        all_chunks.extend(processed_chunks)
    
    return all_chunks
