import re

def fix_mermaid_syntax(diagram_code: str, diagram_type: str = "flowchart") -> str:
    """
    Fix common Mermaid syntax issues to ensure proper rendering with Mermaid v8.14.0.
    This function addresses compatibility issues between newer Mermaid syntax and older versions.
    """
    if not diagram_code:
        # Default empty diagram based on type
        if diagram_type == "flowchart":
            return "graph TD\nA(Empty Diagram)"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        elif diagram_type == "mindmap":
            return "mindmap\nroot((Mindmap))"
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
        # Remove excessive spaces (but preserve spaces in labels)
        line = re.sub(r'^\s+', '', line)  # Remove leading spaces
        line = re.sub(r'\s+$', '', line)  # Remove trailing spaces
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
    
    # Handle flowchart syntax for compatibility with v8.14.0
    if diagram_type == "flowchart":
        # Convert flowchart TD to graph TD for older Mermaid versions
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
            
    # Handle sequence diagram syntax
    elif diagram_type == "sequence":
        if not diagram_code.startswith("sequenceDiagram"):
            diagram_code = "sequenceDiagram\n" + diagram_code
    
    # Handle mindmap diagram syntax (which was introduced in newer versions)
    elif diagram_type == "mindmap":
        # Convert newer mindmap syntax to basic flowchart for compatibility
        if diagram_code.startswith("mindmap"):
            # Extract the lines after mindmap
            mindmap_lines = diagram_code.split('\n')[1:]
            # Create a simple graph TD representation
            diagram_code = "graph TD\n"
            node_counter = 0
            for line in mindmap_lines:
                # Count leading spaces to determine hierarchy level
                leading_spaces = len(line) - len(line.lstrip())
                level = leading_spaces // 2
                content = line.strip()
                if content:
                    node_id = f"Node{node_counter}"
                    diagram_code += f"{node_id}({content})\n"
                    # Connect to previous node if not the first
                    if node_counter > 0:
                        prev_node = f"Node{node_counter-1}"
                        diagram_code += f"{prev_node} --> {node_id}\n"
                    node_counter += 1
        elif not diagram_code.startswith("graph"):
            diagram_code = "graph TD\n" + diagram_code
    
    # Replace bracket nodes with parentheses for better compatibility
    if diagram_type == "flowchart" or diagram_code.startswith("graph"):
        # Convert node definitions with brackets to parentheses
        diagram_code = re.sub(r'([A-Za-z0-9_-]+)\[([^\]]+)\]', r'\1(\2)', diagram_code)
    
    # Fix common syntax issues in flowcharts
    if diagram_type == "flowchart" or diagram_code.startswith("graph"):
        # Fix node definitions with curly braces (decision nodes)
        # Keep the curly braces as they're supported in v8.14.0
        # But ensure proper spacing: A{Text} -> A{Text}
        diagram_code = re.sub(r'([A-Za-z0-9_-]+){([^}]+)}', r'\1{\2}', diagram_code)
        
        # Ensure spaces around arrows
        diagram_code = re.sub(r'(\w+)-->', r'\1 --> ', diagram_code)
        diagram_code = re.sub(r'-->(\w+)', r'--> \1', diagram_code)
        
        # Fix arrow labels to ensure they're properly formatted
        # For example: A -->|Yes| B should have proper spacing
        diagram_code = re.sub(r'\s*-->\|([^|]+)\|\s*', r' -->|\1| ', diagram_code)
        
        # Fix any style attributes - remove them as they often cause issues
        diagram_code = re.sub(r'style\s+\w+\s+.*?\n', '\n', diagram_code)
    
    # Remove potentially problematic styling and interactive features
    # These often cause syntax errors in older versions
    diagram_code = re.sub(r'classDef.*?\n', '\n', diagram_code)  # Remove classDef
    diagram_code = re.sub(r'class\s+.*?\n', '\n', diagram_code)  # Remove class assignments
    diagram_code = re.sub(r'linkStyle.*?\n', '\n', diagram_code)  # Remove linkStyle
    diagram_code = re.sub(r'click.*?\n', '\n', diagram_code)     # Remove click handlers
    diagram_code = re.sub(r':::.*?(?=\s|$)', '', diagram_code)   # Remove CSS-style classes
    
    # Fix any subgraph syntax for better compatibility
    diagram_code = re.sub(r'subgraph\s+([^\n"]+)(?!\s*")', r'subgraph "\1"', diagram_code)
    
    # Remove any comments which could cause issues
    diagram_code = re.sub(r'%%.*?\n', '\n', diagram_code)
    
    # Handle edge case: ensure first line of flowchart has proper orientation
    lines = diagram_code.split('\n')
    if len(lines) > 0 and lines[0].startswith("graph ") and len(lines[0]) <= len("graph "):
        lines[0] = "graph TD"
        diagram_code = '\n'.join(lines)
    
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