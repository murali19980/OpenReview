from typing import List, Dict, Any
from langgraph.graph import StateGraph, END
from graph.state import ReviewState

# Lazy-loaded imports of agent functions to allow staging the graph before complete agent definitions
# They can also be imported directly since we stub them.
from agents.triage_agent import run_triage
from agents.security_agent import run_security
from agents.logic_agent import run_logic
from agents.docs_agent import run_docs
from agents.orchestrator import run_orchestrator

# Node wrapper functions in the LangGraph format: (state) -> state_updates
async def triage_node(state: ReviewState) -> Dict[str, Any]:
    print("[NODE] Starting Triage Node...")
    # Call the actual triage logic
    triage_decisions = await run_triage(state)
    return {
        "triage_decisions": triage_decisions,
        "messages": [{"role": "system", "content": f"Triage complete. Decisions: {triage_decisions}"}]
    }

async def security_agent_node(state: ReviewState) -> Dict[str, Any]:
    print("[NODE] Starting Security Agent Node...")
    findings = await run_security(state)
    return {
        "security_findings": findings,
        "messages": [{"role": "system", "content": "Security agent review completed."}]
    }

async def logic_agent_node(state: ReviewState) -> Dict[str, Any]:
    print("[NODE] Starting Logic Agent Node...")
    findings = await run_logic(state)
    return {
        "logic_findings": findings,
        "messages": [{"role": "system", "content": "Logic agent review completed."}]
    }

async def docs_agent_node(state: ReviewState) -> Dict[str, Any]:
    print("[NODE] Starting Docs Agent Node...")
    findings = await run_docs(state)
    return {
        "docs_findings": findings,
        "messages": [{"role": "system", "content": "Documentation agent review completed."}]
    }

async def orchestrator_node(state: ReviewState) -> Dict[str, Any]:
    print("[NODE] Starting Orchestrator Node...")
    report = await run_orchestrator(state)
    return {
        "final_report": report,
        "messages": [{"role": "system", "content": "Orchestrator compiled the final review report."}]
    }

# Conditional routing logic after triage
def route_after_triage(state: ReviewState) -> List[str]:
    decisions = state.get("triage_decisions", {})
    next_nodes = []
    
    # Check decisions and build list of parallel execution targets
    if decisions.get("security", False):
        next_nodes.append("security_agent")
    if decisions.get("logic", False):
        next_nodes.append("logic_agent")
    if decisions.get("docs", False):
        next_nodes.append("docs_agent")
        
    # If no specialized reviews are selected, go directly to orchestrator
    if not next_nodes:
        print("[ROUTE] No specialized agents selected. Routing straight to Orchestrator.")
        return ["orchestrator"]
        
    print(f"[ROUTE] Routing parallel execution to: {next_nodes}")
    return next_nodes

# Build the LangGraph StateGraph
workflow = StateGraph(ReviewState)

# 1. Add nodes
workflow.add_node("triage", triage_node)
workflow.add_node("security_agent", security_agent_node)
workflow.add_node("logic_agent", logic_agent_node)
workflow.add_node("docs_agent", docs_agent_node)
workflow.add_node("orchestrator", orchestrator_node)

# 2. Add entrypoint
workflow.set_entry_point("triage")

# 3. Add conditional routing from triage to specialized agents or orchestrator
workflow.add_conditional_edges(
    "triage",
    route_after_triage,
    {
        "security_agent": "security_agent",
        "logic_agent": "logic_agent",
        "docs_agent": "docs_agent",
        "orchestrator": "orchestrator"
    }
)

# 4. Connect all specialized agents to the orchestrator (join phase)
workflow.add_edge("security_agent", "orchestrator")
workflow.add_edge("logic_agent", "orchestrator")
workflow.add_edge("docs_agent", "orchestrator")

# 5. Connect orchestrator to final END
workflow.add_edge("orchestrator", END)

# Compile the workflow
app = workflow.compile()
