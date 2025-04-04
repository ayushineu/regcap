import os
import streamlit as st
from openai import OpenAI

# Initialize the OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_answer(question, context_chunks):
    """
    Generate an answer to a question based on context from document chunks.
    
    Args:
        question: The user's question
        context_chunks: List of relevant document chunks
        
    Returns:
        The generated answer
    """
    try:
        # Extract text and source information from chunks
        contexts = []
        sources = set()
        
        for chunk in context_chunks:
            contexts.append(chunk["content"])
            source = f"{chunk['metadata']['source']}, page {chunk['metadata']['page']}"
            sources.add(source)
        
        # Join the context texts
        context_text = "\n\n".join(contexts)
        
        # Format source references
        source_references = "\n".join([f"- {source}" for source in sources])
        
        # Create the system message
        system_message = (
            "You are a regulatory document assistant. Your task is to answer questions based ONLY on the "
            "provided document excerpts. If the information needed to answer the question is not present "
            "in the provided excerpts, state that you cannot find relevant information in the documents. "
            "Do not make up or infer information that is not explicitly stated in the excerpts. "
            "If appropriate, mention the source document and page number in your answer."
        )
        
        # Format the user message with the question and context
        user_message = f"""
Question: {question}

Document excerpts:
{context_text}

Sources:
{source_references}

Based ONLY on the document excerpts above, provide a clear and comprehensive answer to the question.
"""
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,  # Lower temperature for more factual responses
            max_tokens=800
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        st.error(f"Error generating answer: {str(e)}")
        return "I'm sorry, but I encountered an error when trying to generate an answer. Please try again."
