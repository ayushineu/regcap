import re

def fix_mermaid_syntax(diagram_code: str, diagram_type: str = "flowchart") -> str:
    """
    Enhanced Mermaid syntax fixer with robust error handling and simplification
    for compatibility with Mermaid v8.14.0.
    
    This function implements a multi-stage approach:
    1. Extract the diagram code (if wrapped in markdown code blocks)
    2. Normalize and sanitize the content
    3. Fix common syntax patterns for better compatibility
    4. Check for structural integrity and apply simplification if needed
    5. Add proper declarations and format
    """
    # If no diagram code provided, return a default diagram
    if not diagram_code or diagram_code.strip() == "":
        # Default empty diagram based on type
        if diagram_type == "flowchart":
            return "graph TD\nA(Empty Diagram)"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        elif diagram_type == "mindmap":
            return "mindmap\nroot((Mindmap))"
        else:
            return "graph TD\nA(Empty Diagram)"
    
    # STAGE 1: EXTRACT DIAGRAM CODE
    # -----------------------------
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
    
    # STAGE 2: NORMALIZE AND SANITIZE
    # -------------------------------
    # Clean up whitespace and control characters
    diagram_code = diagram_code.strip()
    diagram_code = re.sub(r'[\x00-\x1F\x7F]', '', diagram_code)  # Remove control characters
    
    # Normalize line endings
    diagram_code = diagram_code.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive whitespace but preserve indentation structure
    lines = diagram_code.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if line.strip():  # Skip completely empty lines
            # Normalize indentation to 4 spaces and trim trailing whitespace
            if line.lstrip() != line:  # Line has leading whitespace
                indent_level = len(line) - len(line.lstrip())
                normalized_indent = '    ' * (indent_level // 2)  # Convert any indentation to multiples of 4 spaces
                line = normalized_indent + line.lstrip()
            line = line.rstrip()  # Remove trailing whitespace
            cleaned_lines.append(line)
    
    # If all content was empty, return a default diagram
    if not cleaned_lines:
        if diagram_type == "flowchart":
            return "graph TD\nA(Empty Diagram)"
        elif diagram_type == "sequence":
            return "sequenceDiagram\nA->>B: Empty Diagram"
        else:
            return "graph TD\nA(Empty Diagram)"
    
    # STAGE 3: FIX COMMON SYNTAX PATTERNS
    # -----------------------------------
    # Rebuild the diagram code after cleaning
    diagram_code = '\n'.join(cleaned_lines)
    
    # Check diagram type and ensure proper format declaration
    if diagram_type == "flowchart":
        # Fix flowchart type declarations
        if diagram_code.startswith("flowchart TD"):
            diagram_code = "graph TD" + diagram_code[len("flowchart TD"):]
        elif diagram_code.startswith("flowchart LR"):
            diagram_code = "graph LR" + diagram_code[len("flowchart LR"):]
        elif diagram_code.startswith("flowchart RL"):
            diagram_code = "graph RL" + diagram_code[len("flowchart RL"):]
        elif diagram_code.startswith("flowchart BT"):
            diagram_code = "graph BT" + diagram_code[len("flowchart BT"):]
        # If no proper declaration, add default top-down orientation
        elif not diagram_code.startswith("graph "):
            diagram_code = "graph TD\n" + diagram_code
    elif diagram_type == "sequence":
        if not diagram_code.startswith("sequenceDiagram"):
            diagram_code = "sequenceDiagram\n" + diagram_code
    elif diagram_type == "mindmap" or diagram_type == "mind":
        # Convert mindmaps to flowcharts for better compatibility
        diagram_code = convert_mindmap_to_flowchart(diagram_code)
    
    # STAGE 4: STRUCTURAL INTEGRITY CHECKS & SIMPLIFICATION
    # ----------------------------------------------------
    # For flowcharts, sanitize node definitions and connections
    if diagram_type == "flowchart" or diagram_code.startswith("graph"):
        # Standardize node definitions
        # Convert brackets to parentheses for compatibility
        diagram_code = re.sub(r'([A-Za-z0-9_.-]+)\[([^\]]+)\]', r'\1(\2)', diagram_code)
        
        # Fix node IDs: ensure they start with a letter and contain only valid characters
        # Find node definition patterns like "A(Text)" or "node1(Text)"
        node_defs = re.findall(r'([A-Za-z0-9_.-]+)[\[(]', diagram_code)
        invalid_chars = set()
        
        for node_id in node_defs:
            if not re.match(r'^[A-Za-z][A-Za-z0-9_.-]*$', node_id):
                # This node ID doesn't follow the required pattern
                invalid_chars.update([c for c in node_id if not c.isalnum() and c not in '_.-'])
        
        # If we found invalid characters, clean them from node IDs
        if invalid_chars:
            for char in invalid_chars:
                diagram_code = diagram_code.replace(char, '_')
        
        # Fix connection syntax (arrows)
        # Ensure proper spaces around arrows
        diagram_code = re.sub(r'(\w+)-->', r'\1 --> ', diagram_code)
        diagram_code = re.sub(r'-->(\w+)', r'--> \1', diagram_code)
        
        # Fix arrow labels (e.g., A -->|Yes| B)
        diagram_code = re.sub(r'\s*-->\|([^|]+)\|\s*', r' -->|\1| ', diagram_code)
        
        # Check for structural errors
        has_structural_errors = check_structural_errors(diagram_code)
        
        if has_structural_errors:
            # Attempt to simplify the diagram
            diagram_code = simplify_flowchart(diagram_code)
    
    # STAGE 5: FINAL CLEANUP
    # ---------------------
    # Remove potentially problematic styling and interactive features
    diagram_code = re.sub(r'style\s+\w+\s+.*?\n', '\n', diagram_code)  # Remove style definitions
    diagram_code = re.sub(r'classDef.*?\n', '\n', diagram_code)  # Remove classDef
    diagram_code = re.sub(r'class\s+.*?\n', '\n', diagram_code)  # Remove class assignments
    diagram_code = re.sub(r'linkStyle.*?\n', '\n', diagram_code)  # Remove linkStyle
    diagram_code = re.sub(r'click.*?\n', '\n', diagram_code)     # Remove click handlers
    diagram_code = re.sub(r':::.*?(?=\s|$)', '', diagram_code)   # Remove CSS-style classes
    
    # Fix subgraph syntax
    diagram_code = re.sub(r'subgraph\s+([^\n"]+)(?!\s*")', r'subgraph "\1"', diagram_code)
    
    # Remove comments
    diagram_code = re.sub(r'%%.*?\n', '\n', diagram_code)
    
    # Ensure proper orientation in first line
    lines = diagram_code.split('\n')
    if len(lines) > 0 and lines[0].startswith("graph ") and len(lines[0]) <= len("graph "):
        lines[0] = "graph TD"
        diagram_code = '\n'.join(lines)
    
    return diagram_code

def check_structural_errors(diagram_code):
    """
    Check for common structural errors in Mermaid diagrams
    Returns True if structural errors are detected
    """
    # Look for common error patterns
    
    # Check for unmatched brackets or parentheses
    open_count = diagram_code.count('(') + diagram_code.count('[') + diagram_code.count('{')
    close_count = diagram_code.count(')') + diagram_code.count(']') + diagram_code.count('}')
    if open_count != close_count:
        return True
    
    # Check for lines with arrow syntax errors
    arrow_pattern = r'-->'
    lines = diagram_code.split('\n')
    for line in lines:
        if '-->' in line:
            # Check if line has proper node --> node format
            if not re.match(r'^\s*[A-Za-z0-9_.-]+.*-->.*[A-Za-z0-9_.-]+', line):
                return True
    
    # Check for subgraph errors
    if 'subgraph' in diagram_code and 'end' not in diagram_code:
        return True
    
    return False

def simplify_flowchart(diagram_code):
    """
    Simplify a flowchart by:
    1. Removing nested structures (subgraphs)
    2. Simplifying complex connections
    3. Ensuring all nodes are properly defined
    """
    # Extract the direction (TD, LR, etc.)
    direction = "TD"  # Default to top-down
    if diagram_code.startswith("graph "):
        direction_match = re.match(r'graph\s+([A-Z]{2})', diagram_code)
        if direction_match:
            direction = direction_match.group(1)
    
    # Start with a clean diagram
    simplified = f"graph {direction}\n"
    
    # Extract all node definitions and connections
    lines = diagram_code.split('\n')
    node_defs = []
    connections = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("subgraph") or stripped == "end":
            continue
        elif "-->" in stripped:
            connections.append(stripped)
        elif re.match(r'^[A-Za-z0-9_.-]+[\[(]', stripped):
            node_defs.append(stripped)
    
    # Add node definitions to simplified diagram
    for node in node_defs:
        simplified += f"    {node}\n"
    
    # Add simplified connections
    for conn in connections:
        simplified += f"    {conn}\n"
    
    return simplified

def convert_mindmap_to_flowchart(mindmap_code):
    """
    Convert a mindmap diagram to a flowchart
    """
    # Create a basic flowchart structure
    flowchart = "graph TD\n"
    
    # Extract nodes from the mindmap
    lines = mindmap_code.split('\n')
    nodes = []
    
    # Skip the first line if it's the mindmap declaration
    start_idx = 1 if mindmap_code.startswith("mindmap") else 0
    
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        
        # Look for node patterns
        if re.match(r'^[*+-]\s+', line):  # Bullet point style
            node_text = re.sub(r'^[*+-]\s+', '', line)
            nodes.append(node_text)
        elif re.match(r'^\w+\((.*?)\)', line):  # Node with parentheses
            matches = re.match(r'^\w+\((.*?)\)', line)
            if matches:
                nodes.append(matches.group(1))
    
    # If we found some nodes, create a simple hierarchy
    if nodes:
        flowchart += f"    A({nodes[0]})\n"
        
        for i, node in enumerate(nodes[1:], 1):
            node_id = chr(65 + i) if i < 26 else f"N{i}"
            flowchart += f"    {node_id}({node})\n"
            
            # Connect to root or previous node
            if i <= 3:  # First level nodes connect to root
                flowchart += f"    A --> {node_id}\n"
            else:  # Other nodes connect to the appropriate parent
                parent_id = chr(65 + (i % 3) + 1)  # Simple algorithm to distribute connections
                flowchart += f"    {parent_id} --> {node_id}\n"
    else:
        # Default simple flowchart
        flowchart += "    A(Main Topic)\n"
        flowchart += "    B(Subtopic 1)\n"
        flowchart += "    C(Subtopic 2)\n"
        flowchart += "    A --> B\n"
        flowchart += "    A --> C\n"
    
    return flowchart

if __name__ == "__main__":
    # Test the function with multiple sample diagrams
    
    # Test 1: Standard flowchart
    test_diagram1 = '''
    flowchart TD
        A[Start] --> B[Process]
        B --> C{Decision}
        C -->|Yes| D[End]
        C -->|No| B
        
        style A fill:#f9f,stroke:#333,stroke-width:4px
        click A callback "Tooltip"
        classDef default fill:#f9f,stroke:#333,stroke-width:2px
    '''
    
    # Test 2: Broken syntax flowchart
    test_diagram2 = '''
    flowchart TD
        A[Start Process] --> B[Middle
        B --> C{Decision Point
        C -->|Yes Branch| D[End
        C -->|No| B
    '''
    
    # Test 3: Stress test related flowchart 
    test_diagram3 = '''
    flowchart TD
        A[U.S. Stress Tests] --> B[Financial Crisis Response]
        B --> C[Identify Capital Needs]
        B --> D[Bolster Public Confidence]
        A --> E[Ongoing Supervision]
        E --> F[Capital Planning]
        E --> G[Risk Management]
        A --> H[Effects on Banking]
        H --> I[Credit Supply]
        H --> J[Loan Spreads]
    '''
    
    # Test fix_mermaid_syntax on all diagrams
    print("TEST 1: STANDARD FLOWCHART")
    fixed1 = fix_mermaid_syntax(test_diagram1, "flowchart")
    print("\nOriginal:")
    print(test_diagram1)
    print("\nFixed:")
    print(fixed1)
    
    print("\n\nTEST 2: BROKEN SYNTAX")
    fixed2 = fix_mermaid_syntax(test_diagram2, "flowchart")
    print("\nOriginal:")
    print(test_diagram2)
    print("\nFixed:")
    print(fixed2)
    
    print("\n\nTEST 3: STRESS TEST FLOWCHART")
    fixed3 = fix_mermaid_syntax(test_diagram3, "flowchart")
    print("\nOriginal:")
    print(test_diagram3)
    print("\nFixed:")
    print(fixed3)