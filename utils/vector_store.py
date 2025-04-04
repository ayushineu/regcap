import numpy as np
import faiss
import streamlit as st
import openai
import os
from openai import OpenAI

# Initialize the OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text):
    """
    Get the embedding for a text using OpenAI's embeddings API.
    
    Args:
        text: The text to embed
        
    Returns:
        The embedding vector as a numpy array
    """
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"  # Using Ada embedding model
        )
        embedding = response.data[0].embedding
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        st.error(f"Error generating embedding: {str(e)}")
        return None

def create_vector_store(chunks):
    """
    Create a FAISS vector store from text chunks.
    
    Args:
        chunks: List of document chunks, each with "content" and "metadata"
        
    Returns:
        A dict containing the vector store and associated data
    """
    try:
        # Extract text content from chunks
        texts = [chunk["content"] for chunk in chunks]
        
        # Generate embeddings for each chunk
        embeddings = []
        for i, text in enumerate(texts):
            with st.status(f"Creating embeddings: {i+1}/{len(texts)}"):
                embedding = get_embedding(text)
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    st.warning(f"Skipping chunk {i+1} due to embedding error")
        
        if not embeddings:
            st.error("Failed to create any embeddings.")
            return None
        
        # Convert list of embeddings to a 2D numpy array
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Create the FAISS index
        dimension = embeddings_array.shape[1]  # Get the dimensionality of the embeddings
        index = faiss.IndexFlatL2(dimension)  # Using L2 distance for similarity
        index.add(embeddings_array)
        
        # Return a dictionary with the index and associated data
        return {
            "index": index,
            "chunks": chunks[:len(embeddings)],  # Only include chunks that have embeddings
            "embeddings": embeddings_array
        }
    except Exception as e:
        st.error(f"Error creating vector store: {str(e)}")
        return None

def get_similar_chunks(query, vector_store, top_k=5):
    """
    Find chunks similar to the query in the vector store.
    
    Args:
        query: The user query
        vector_store: The vector store containing document embeddings
        top_k: Number of similar chunks to retrieve
        
    Returns:
        A list of relevant text chunks
    """
    try:
        # Check if vector_store has the required keys
        if not vector_store or "chunks" not in vector_store:
            st.warning("No document chunks available in vector store.")
            return []
            
        # If index doesn't exist, try to rebuild it using get_vector_store from db_manager
        if "index" not in vector_store:
            st.info("Rebuilding vector index...")
            from utils.db_manager import get_vector_store
            try:
                # Try to rebuild the vector store from database
                current_session_vector_store = get_vector_store()
                if current_session_vector_store and "index" in current_session_vector_store:
                    vector_store = current_session_vector_store
                else:
                    # Rebuild index on the fly if database retrieval fails
                    chunks = vector_store.get("chunks", [])
                    embeddings = []
                    for chunk in chunks:
                        embedding = get_embedding(chunk["content"])
                        if embedding is not None:
                            embeddings.append(embedding)
                    
                    if not embeddings:
                        st.warning("Could not generate embeddings for chunks.")
                        return []
                    
                    # Build the index
                    embeddings_array = np.array(embeddings).astype('float32')
                    dimension = embeddings_array.shape[1]
                    index = faiss.IndexFlatL2(dimension)
                    index.add(embeddings_array)
                    
                    # Add to vector_store
                    vector_store["index"] = index
                    vector_store["embeddings"] = embeddings_array
            except Exception as rebuild_error:
                st.error(f"Error rebuilding vector index: {str(rebuild_error)}")
                return []
        
        # Generate embedding for the query
        query_embedding = get_embedding(query)
        if query_embedding is None:
            st.warning("Failed to generate embedding for your query.")
            return []
        
        # Reshape query embedding to match FAISS requirements
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search the index
        distances, indices = vector_store["index"].search(query_embedding, k=min(top_k, len(vector_store["chunks"])))
        
        # Collect the similar chunks
        similar_chunks = []
        for i in indices[0]:
            if i < len(vector_store["chunks"]):
                chunk = vector_store["chunks"][i]
                similar_chunks.append(chunk)
        
        return similar_chunks
    except Exception as e:
        st.error(f"Error searching vector store: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return []
