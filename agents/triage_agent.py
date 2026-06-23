import os
from typing import Dict, Any, List
from graph.state import ReviewState

async def run_triage(state: ReviewState) -> Dict[str, bool]:
    """
    Triage Agent: Analyzes changed files in the PR to determine which specialized reviews to run.
    This saves token budget and prevents unnecessary agent executions on unrelated files.
    """
    print("[AGENT] Triage Agent analyzing changed files...")
    
    changed_files: List[str] = state.get("changed_files", [])
    
    # Define file extension categories
    code_extensions = {".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".rs"}
    docs_extensions = {".md", ".txt", ".rst", ".adoc", ".json", ".yaml", ".yml"}
    
    run_security = False
    run_logic = False
    run_docs = False
    
    # If no files are specified, run all as a fallback
    if not changed_files:
        print("[AGENT] No changed files detected in state. Running all specialist agents as fallback.")
        return {
            "security": True,
            "logic": True,
            "docs": True
        }
        
    for file in changed_files:
        _, ext = os.path.splitext(file.lower())
        if ext in code_extensions:
            run_security = True
            run_logic = True
        elif ext in docs_extensions:
            run_docs = True
            
    # Return routing decisions
    decisions = {
        "security": run_security,
        "logic": run_logic,
        "docs": run_docs
    }
    
    print(f"[AGENT] Triage Decisions: {decisions}")
    return decisions
