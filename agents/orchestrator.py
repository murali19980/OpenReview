import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import config
from graph.state import ReviewState

# Prompt template for Orchestrator compilation
ORCHESTRATOR_PROMPT_TEMPLATE = """
You are a Principal Software Engineer and Code Review Lead.
Your task is to take reviews from specialized agents and compile them into a unified, developer-friendly, professional GitHub PR comment.

Here are the findings from the specialized review runs:

### SECURITY AUDIT FINDINGS:
{security_section}

### LOGIC & CORRECTNESS REVIEW:
{logic_section}

### DOCUMENTATION SUMMARY & GAPS:
{docs_section}

Please compile these sections into a cohesive, high-quality, professional code review report.
Your output MUST:
1. Start with a brief, high-level, encouraging summary of the PR (e.g., "Overall, this PR introduces X. It looks great but has a few minor issues to resolve...").
2. Include clear headings for Security, Logic, and Documentation.
3. Keep the language constructive, professional, and action-oriented.
4. If an agent returned that no issues were found in their respective category, make sure to note that with a positive indicator (e.g., "✅ Security: No issues found").
5. Do NOT invent any new code bugs, vulnerabilities, or changes not mentioned in the findings above.

Ensure your entire output is valid GitHub Flavored Markdown.
"""

def extract_bug_report(logic_output: str) -> str:
    """
    Extracts the bug report from logic agent output, stripping the thinking chain.
    """
    if not logic_output:
        return "No logic bugs or issues detected."
    # Look for <bug_report>...</bug_report>
    match = re.search(r"<bug_report>(.*?)</bug_report>", logic_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback if tags are missing
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", logic_output, flags=re.DOTALL | re.IGNORECASE).strip()
    return cleaned if cleaned else logic_output

def format_security_findings(security_json_str: str) -> str:
    """
    Parses security JSON findings and formats them into a clean Markdown table.
    """
    if not security_json_str:
        return "✅ No security issues detected."
        
    try:
        data = json.loads(security_json_str)
        findings = data.get("findings", [])
        if not findings:
            return "✅ No security vulnerabilities or leaked secrets detected."
        
        md = "| File | Line | Severity | Description |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for f in findings:
            file = f.get("file", "Unknown")
            line = f.get("line", "N/A")
            severity = f.get("severity", "LOW")
            desc = f.get("description", "")
            
            # Emoji mapping for severity
            sev_emoji = "🛡️ LOW"
            if severity.upper() == "HIGH":
                sev_emoji = "🚨 HIGH"
            elif severity.upper() in ("MED", "MEDIUM"):
                sev_emoji = "⚠️ MEDIUM"
                
            md += f"| `{file}` | `{line}` | {sev_emoji} | {desc} |\n"
        return md
    except Exception as e:
        return f"Error parsing security findings: {str(e)}\nRaw findings: {security_json_str}"

async def run_orchestrator(state: ReviewState) -> str:
    """
    Orchestrator Agent: Gathers outputs from Security, Logic, and Docs agents,
    formats/cleans them, and compiles the final unified Markdown review comment.
    """
    print("[AGENT] Orchestrator compiling final review report...")
    
    # Extract findings from state
    raw_security = state.get("security_findings", "")
    raw_logic = state.get("logic_findings", "")
    raw_docs = state.get("docs_findings", "")
    
    # Apply format cleanup
    security_section = format_security_findings(raw_security) if state.get("triage_decisions", {}).get("security", True) else "⏭️ Security review skipped by Triage."
    logic_section = extract_bug_report(raw_logic) if state.get("triage_decisions", {}).get("logic", True) else "⏭️ Logic review skipped by Triage."
    docs_section = raw_docs if state.get("triage_decisions", {}).get("docs", True) else "⏭️ Documentation review skipped by Triage."
    
    if not config.OPENROUTER_API_KEY:
        print("[AGENT] OPENROUTER_API_KEY not configured. Compiling a basic direct report.")
        # Fallback basic compile
        return f"# Code Review Report (Fallback)\n\n### Security\n{security_section}\n\n### Logic\n{logic_section}\n\n### Docs\n{docs_section}"

    # Prepare LLM client
    llm = ChatOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        model=config.PRIMARY_MODEL,
        default_headers={
            "HTTP-Referer": "https://github.com/murali19980/OpenReview",
            "X-Title": "OpenReview Orchestrator"
        },
        temperature=0.3
    )

    prompt = PromptTemplate(
        template=ORCHESTRATOR_PROMPT_TEMPLATE,
        input_variables=["security_section", "logic_section", "docs_section"]
    )
    
    formatted_prompt = prompt.format(
        security_section=security_section,
        logic_section=logic_section,
        docs_section=docs_section
    )
    
    try:
        response = await llm.ainvoke(formatted_prompt)
        report = response.content.strip()
        print("[AGENT] Orchestrator final report compiled successfully.")
        return report
        
    except Exception as e:
        print(f"[ERROR] Orchestrator failed to compile report: {str(e)}")
        return f"# Code Review Report (Error Compile)\n\nAn error occurred during final report generation: {str(e)}\n\n### Security\n{security_section}\n\n### Logic\n{logic_section}\n\n### Docs\n{docs_section}"
