import os
import streamlit as st
from openai import OpenAI
import json

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

def generate_diagram(question, context_chunks, diagram_type="flowchart"):
    """
    Generate a Mermaid diagram based on document context and a question.
    
    Args:
        question: The user's question about generating a diagram
        context_chunks: List of relevant document chunks
        diagram_type: Type of diagram to generate (flowchart, sequence, mindmap)
        
    Returns:
        A tuple containing (success status, diagram code or error message)
    """
    try:
        # Extract text from chunks
        contexts = []
        
        for chunk in context_chunks:
            contexts.append(chunk["content"])
        
        # Join the context texts
        context_text = "\n\n".join(contexts)
        
        # Define diagram templates
        diagram_templates = {
            "flowchart": "flowchart TD",
            "sequence": "sequenceDiagram",
            "mindmap": "mindmap",
            "classDiagram": "classDiagram"
        }
        
        template_start = diagram_templates.get(diagram_type, "flowchart TD")
        
        # Create the system message for diagram generation
        system_message = (
            f"You are a diagram generation assistant specialized in creating Mermaid.js diagrams to visualize "
            f"regulatory concepts and relationships. Based ONLY on the provided document excerpts, create a "
            f"{diagram_type} that addresses the user's question. "
            f"Your response should be VALID Mermaid.js code starting with {template_start} and should visually "
            f"represent concepts, relationships, and processes described in the excerpts. "
            f"If there's not enough information to create a meaningful diagram, explain why. "
            f"Return your response in JSON format with two fields: 'diagram_code' containing the Mermaid code and "
            f"'explanation' containing a brief explanation of what the diagram represents."
        )
        
        # Create user message
        user_message = f"""
Document excerpts:
{context_text}

Question/Request: {question}

Please create a {diagram_type} diagram that visually represents the key concepts and relationships described in these document excerpts.

Remember to focus ONLY on what is explicitly stated in the documents.
"""
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        
        # Validate the diagram code
        if "diagram_code" not in result or not result["diagram_code"]:
            return False, "Could not generate a diagram from the document content."
        
        return True, result
    
    except Exception as e:
        error_msg = f"Error generating diagram: {str(e)}"
        st.error(error_msg)
        return False, error_msg

def detect_diagram_request(question):
    """
    Detect if a user question is requesting a diagram or visualization.
    
    Args:
        question: The user's question
        
    Returns:
        A tuple of (is_diagram_request, diagram_type)
    """
    # Keywords that might indicate a request for visualization
    diagram_keywords = [
        "diagram", "visual", "visualize", "flow", "flowchart", "chart", 
        "graph", "illustration", "visualisation", "visualization", "map", 
        "picture", "schematic", "sequence", "workflow", "process flow",
        "mind map", "relationship", "hierarchy", "structure", "framework",
        "concept map", "organize", "draw", "illustrate", "sketch", "create a visual",
        "graphical", "representation"
    ]
    
    # Check if any of the diagram keywords are in the question
    question_lower = question.lower()
    if any(keyword in question_lower for keyword in diagram_keywords):
        # Determine the diagram type based on the question
        if any(term in question_lower for term in ["sequence", "timeline", "step by step"]):
            return True, "sequence"
        elif any(term in question_lower for term in ["mind map", "concept map", "brain"]):
            return True, "mindmap"
        elif any(term in question_lower for term in ["class", "object", "entity"]):
            return True, "classDiagram"
        else:
            return True, "flowchart"  # Default to flowchart
    
    return False, None
