import time
import json
import os
from fix_mermaid import fix_mermaid_syntax

# Sample flowchart diagram with common syntax issues
flowchart_test = '''
flowchart TD
    A[Start] --> B[Process 1]
    B --> C{Decision?}
    C -->|Yes| D[Process 2]
    C -->|No| E[Process 3]
    D --> F[End]
    E --> F
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    classDef default fill:#f9f,stroke:#333,stroke-width:1px
'''

# Sample sequence diagram
sequence_test = '''
sequenceDiagram
    participant User
    participant System
    participant API
    
    User->>System: Request Information
    System->>API: Query Data
    API-->>System: Return Results
    System-->>User: Display Information
    
    Note over User,System: Interaction Complete
'''

# Sample mindmap (newer syntax)
mindmap_test = '''
mindmap
  root((Regulatory Framework))
    Compliance
      Internal Controls
      Reporting Requirements
    Risk Management
      Identification
      Assessment
      Mitigation
    Governance
      Board Oversight
      Management Responsibility
'''

# Print raw diagram for debugging
print("Raw mindmap test structure:")
for i, line in enumerate(mindmap_test.split('\n')):
    print(f"{i}: '{line}'")
print()

# Process and test each diagram
def test_diagram(diagram_code, diagram_type):
    print(f"\n--- Original {diagram_type.upper()} Diagram ---")
    print(diagram_code)
    
    fixed_code = fix_mermaid_syntax(diagram_code, diagram_type)
    
    print(f"\n--- Fixed {diagram_type.upper()} Diagram ---")
    print(fixed_code)
    print("-----------------------------------\n")

if __name__ == "__main__":
    # Test each diagram type
    test_diagram(flowchart_test, "flowchart")
    test_diagram(sequence_test, "sequence")
    test_diagram(mindmap_test, "mindmap")
    
    print("All tests completed.")