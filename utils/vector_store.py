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
        # Generate embedding for the query
        query_embedding = get_embedding(query)
        if query_embedding is None:
            return []
        
        # Reshape query embedding to match FAISS requirements
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search the index
        distances, indices = vector_store["index"].search(query_embedding, k=top_k)
        
        # Collect the similar chunks
        similar_chunks = []
        for i in indices[0]:
            if i < len(vector_store["chunks"]):
                chunk = vector_store["chunks"][i]
                similar_chunks.append(chunk)
        
        return similar_chunks
    except Exception as e:
        st.error(f"Error searching vector store: {str(e)}")
        return []
