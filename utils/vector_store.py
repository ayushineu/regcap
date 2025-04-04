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
        if not chunks:
            st.warning("No chunks provided to create vector store.")
            return {"chunks": []}  # Return empty store instead of None
        
        # Extract text content from chunks
        processed_chunks = []
        embeddings = []
        
        # Process chunks in smaller batches to avoid timeouts
        max_batch_size = 10
        total_chunks = len(chunks)
        
        for i in range(0, total_chunks, max_batch_size):
            batch_end = min(i + max_batch_size, total_chunks)
            st.info(f"Processing chunks {i+1} to {batch_end} of {total_chunks}")
            
            for j in range(i, batch_end):
                chunk = chunks[j]
                try:
                    # Skip chunks with no content
                    if not chunk.get("content"):
                        continue
                    
                    # Get embedding for the chunk
                    embedding = get_embedding(chunk["content"])
                    if embedding is not None:
                        embeddings.append(embedding)
                        processed_chunks.append(chunk)
                except Exception as chunk_error:
                    st.warning(f"Error processing chunk {j+1}: {str(chunk_error)}")
                    continue  # Skip this chunk and continue
        
        # Return early if no embeddings were created
        if not embeddings:
            st.warning("Could not create any embeddings. Returning chunks only.")
            return {"chunks": processed_chunks}
        
        try:
            # Convert list of embeddings to a 2D numpy array
            embeddings_array = np.array(embeddings).astype('float32')
            
            # Create the FAISS index
            dimension = embeddings_array.shape[1]  # Get the dimensionality of the embeddings
            index = faiss.IndexFlatL2(dimension)  # Using L2 distance for similarity
            index.add(embeddings_array)
            
            # Return a dictionary with the index and associated data
            return {
                "index": index,
                "chunks": processed_chunks,  # Only include chunks that have embeddings
                "embeddings": embeddings_array
            }
        except Exception as array_error:
            st.warning(f"Error creating index: {str(array_error)}")
            # If index creation fails, still return the chunks
            return {"chunks": processed_chunks}
            
    except Exception as e:
        st.error(f"Error creating vector store: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        # Return empty data rather than None to avoid crashes
        return {"chunks": []}

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
            
        # If no chunks available, return empty list
        chunks = vector_store.get("chunks", [])
        if not chunks:
            st.warning("Vector store contains no document chunks.")
            return []
            
        # If we only have chunks but no index, try a simple keyword matching approach as fallback
        if "index" not in vector_store:
            try:
                # Try to rebuild the index first
                st.info("No vector index found. Attempting to rebuild...")
                
                # First try getting from database
                try:
                    from utils.db_manager import get_vector_store
                    db_vector_store = get_vector_store()
                    if db_vector_store and "index" in db_vector_store:
                        vector_store = db_vector_store
                    else:
                        # Build a new index from chunks
                        embeddings = []
                        valid_chunks = []
                        
                        # Process in smaller batches
                        max_batch = 10
                        for i in range(0, len(chunks), max_batch):
                            batch = chunks[i:i+max_batch]
                            for chunk in batch:
                                if "content" in chunk:
                                    embedding = get_embedding(chunk["content"])
                                    if embedding is not None:
                                        embeddings.append(embedding)
                                        valid_chunks.append(chunk)
                        
                        if embeddings:
                            # Build the index
                            embeddings_array = np.array(embeddings).astype('float32')
                            dimension = embeddings_array.shape[1]
                            index = faiss.IndexFlatL2(dimension)
                            index.add(embeddings_array)
                            
                            # Update vector_store
                            vector_store["index"] = index
                            vector_store["embeddings"] = embeddings_array
                            vector_store["chunks"] = valid_chunks
                        else:
                            # Fallback to keyword matching if we can't build the index
                            raise Exception("Could not build vector index, using keyword matching instead")
                except Exception as rebuild_error:
                    st.warning(f"Index rebuilding failed: {str(rebuild_error)}")
                    
                    # Fallback: Simple keyword matching when FAISS index is unavailable
                    st.info("Using keyword matching as fallback...")
                    keywords = query.lower().split()
                    matched_chunks = []
                    
                    for chunk in chunks:
                        content = chunk.get("content", "").lower()
                        # Count how many keywords are in this chunk
                        matches = sum(1 for keyword in keywords if keyword in content)
                        if matches > 0:
                            # Add match count as a property for sorting
                            chunk_copy = chunk.copy()
                            chunk_copy["_match_score"] = matches
                            matched_chunks.append(chunk_copy)
                    
                    # Sort by match score
                    if matched_chunks:
                        matched_chunks.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
                        # Return top matches
                        return matched_chunks[:min(top_k, len(matched_chunks))]
                    else:
                        return []
            except Exception as fallback_error:
                st.error(f"Error in fallback retrieval: {str(fallback_error)}")
                return []
            
        # If we have a valid index, use it for retrieval
        if "index" in vector_store:
            # Generate embedding for the query
            query_embedding = get_embedding(query)
            if query_embedding is None:
                st.warning("Failed to generate embedding for your query. Using keyword matching instead.")
                # Fallback to keyword matching
                keywords = query.lower().split()
                matched_chunks = []
                for chunk in chunks:
                    content = chunk.get("content", "").lower()
                    if any(keyword in content for keyword in keywords):
                        matched_chunks.append(chunk)
                return matched_chunks[:min(top_k, len(matched_chunks))]
            
            # Reshape query embedding to match FAISS requirements
            query_embedding = np.array([query_embedding]).astype('float32')
            
            try:
                # Search the index
                k_value = min(top_k, len(vector_store["chunks"]))
                if k_value <= 0:
                    return []
                    
                distances, indices = vector_store["index"].search(query_embedding, k=k_value)
                
                # Collect the similar chunks
                similar_chunks = []
                for i in indices[0]:
                    if i < len(vector_store["chunks"]):
                        chunk = vector_store["chunks"][i]
                        similar_chunks.append(chunk)
                
                return similar_chunks
            except Exception as search_error:
                st.warning(f"Error searching vector index: {str(search_error)}. Using fallback method.")
                # Fallback to simple matching
                return chunks[:min(top_k, len(chunks))]
        
        # If we somehow didn't return yet, just return some chunks
        return chunks[:min(top_k, len(chunks))]
    except Exception as e:
        st.error(f"Error searching vector store: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        # Return some chunks anyway rather than an empty list
        if vector_store and "chunks" in vector_store and vector_store["chunks"]:
            return vector_store["chunks"][:min(top_k, len(vector_store["chunks"]))]
        return []
