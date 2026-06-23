from typing import TypedDict, List, Dict, Any, Annotated
import operator

class ReviewState(TypedDict):
    """
    Represents the state of our code review workflow.
    """
    # Pull Request Metadata
    repo_owner: str
    repo_name: str
    pr_number: int
    title: str
    description: str
    diff: str
    changed_files: List[str]
    
    # Triage Decisions (identifies which specialized agents need to run)
    # Example: {"security": True, "logic": True, "docs": False}
    triage_decisions: Dict[str, bool]
    
    # Semantic Code Context and past PR context retrieved from ChromaDB
    retrieved_context: str
    
    # Outputs from specialized agents
    security_findings: str
    logic_findings: str
    docs_findings: str
    
    # The final compiled report written by the Orchestrator
    final_report: str
    
    # Execution logs / step messages
    messages: Annotated[List[Dict[str, Any]], operator.add]
