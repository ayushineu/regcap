import re

def fix_mermaid_syntax(diagram_code: str, diagram_type: str = "flowchart") -> str:
    """Fix common Mermaid syntax issues to ensure proper rendering with older Mermaid versions."""
    if not diagram_code:
        # Default empty diagram based on type
        if diagram_type == "flowchart":
            return "graph TD\nA(Empty Diagram)"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        else:
            return "graph TD\nA(Empty Diagram)"
    
    # Clean up whitespace and control characters
    diagram_code = diagram_code.strip()
    diagram_code = re.sub(r'[\x00-\x1F\x7F]', '', diagram_code)  # Remove control characters
    
    # Remove markdown code block syntax if present
    if "```" in diagram_code:
        # Extract content between ```mermaid and ```
        if "```mermaid" in diagram_code:
            match = re.search(r'```mermaid\n(.*?)```', diagram_code, re.DOTALL)
            if match:
                diagram_code = match.group(1).strip()
        else:
            # Extract content between ``` and ```
            match = re.search(r'```\n?(.*?)```', diagram_code, re.DOTALL)
            if match:
                diagram_code = match.group(1).strip()
    
    # Normalize line endings
    diagram_code = diagram_code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines for processing
    lines = diagram_code.split('\n')
    cleaned_lines = []
    
    # Process each line
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        # Remove excessive spaces
        line = re.sub(r'\s+', ' ', line.strip())
        cleaned_lines.append(line)
    
    if not cleaned_lines:
        # If all lines were removed, return a default diagram
        if diagram_type == "flowchart":
            return "graph TD\nA(Empty Diagram)"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        else:
            return "graph TD\nA(Empty Diagram)"
    
    # Rebuild the diagram code
    diagram_code = '\n'.join(cleaned_lines)
    
    # CRITICAL FIX: Convert flowchart TD to graph TD for older Mermaid versions
    if diagram_type == "flowchart":
        if diagram_code.startswith("flowchart TD"):
            diagram_code = "graph TD" + diagram_code[len("flowchart TD"):]
        elif diagram_code.startswith("flowchart LR"):
            diagram_code = "graph LR" + diagram_code[len("flowchart LR"):]
        elif diagram_code.startswith("flowchart RL"):
            diagram_code = "graph RL" + diagram_code[len("flowchart RL"):]
        elif diagram_code.startswith("flowchart BT"):
            diagram_code = "graph BT" + diagram_code[len("flowchart BT"):]
        elif not diagram_code.startswith("graph"):
            diagram_code = "graph TD\n" + diagram_code
            
    elif diagram_type == "sequence":
        if not diagram_code.startswith("sequenceDiagram"):
            diagram_code = "sequenceDiagram\n" + diagram_code
    
    # Replace bracket nodes with parentheses for better compatibility
    if diagram_type == "flowchart" or diagram_code.startswith("graph"):
        # Convert node definitions with brackets to parentheses
        diagram_code = re.sub(r'([A-Za-z0-9_-]+)\[([^\]]+)\]', r'\1(\2)', diagram_code)
    
    # Remove any fancy styling like classDef or class assignments
    diagram_code = re.sub(r'classDef.*?\n', '\n', diagram_code)
    diagram_code = re.sub(r'class.*?\n', '\n', diagram_code)
    
    # Remove any linkStyle declarations
    diagram_code = re.sub(r'linkStyle.*?\n', '\n', diagram_code)
    
    # Remove any click handlers
    diagram_code = re.sub(r'click.*?\n', '\n', diagram_code)
    
    # Fix any subgraph syntax if present (make it simpler)
    diagram_code = re.sub(r'subgraph\s+([^\n]+)', r'subgraph "\1"', diagram_code)
    
    # Remove any CSS-style classes
    diagram_code = re.sub(r':::.*?(?=\s|$)', '', diagram_code)
    
    # Ensure spaces around arrows for flowcharts
    if diagram_type == "flowchart" or diagram_code.startswith("graph"):
        diagram_code = re.sub(r'(\w+)-->', r'\1 --> ', diagram_code)
        diagram_code = re.sub(r'-->(\w+)', r'--> \1', diagram_code)
        
        # Fix any style attributes
        diagram_code = re.sub(r'style\s+\w+\s+.*?\n', '\n', diagram_code)
    
    return diagram_code

if __name__ == "__main__":
    # Test the function with a sample diagram
    test_diagram = '''
    flowchart TD
        A[Start] --> B[Process]
        B --> C{Decision}
        C -->|Yes| D[End]
        C -->|No| B
        
        style A fill:#f9f,stroke:#333,stroke-width:4px
        click A callback "Tooltip"
        classDef default fill:#f9f,stroke:#333,stroke-width:2px
    '''
    
    fixed = fix_mermaid_syntax(test_diagram, "flowchart")
    print("Original:")
    print(test_diagram)
    print("\nFixed:")
    print(fixed)