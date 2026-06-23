import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import config
from graph.state import ReviewState

# 1. Define the Pydantic model for structured security findings
class SecurityFinding(BaseModel):
    file: str = Field(description="The path of the file containing the issue.")
    line: str = Field(description="The line number or line range where the issue resides. Use 'N/A' if it spans multiple or is generic.")
    severity: str = Field(description="The severity level of the vulnerability: HIGH, MED, or LOW.")
    description: str = Field(description="Detailed explanation of the vulnerability, secret leak, or OWASP violation, and instructions on how to fix it.")

class SecurityReport(BaseModel):
    findings: List[SecurityFinding] = Field(description="A list of all detected security issues.")

# Initialize the Pydantic Output Parser
security_parser = PydanticOutputParser(pydantic_object=SecurityReport)

# 2. Define system prompt for the Security Agent
SECURITY_PROMPT_TEMPLATE = """
You are an expert security engineer and Senior DevSecOps auditor.
Your job is to inspect code diffs and locate security vulnerabilities, secret leaks, API credential disclosures, and OWASP Top 10 issues (such as injection, broken auth, XSS, etc.).

Analyze the PR code changes and look for:
1. Hardcoded API keys, secrets, tokens, passwords, or certificates.
2. Insecure encryption, hashing algorithms, or weak random generators.
3. SQL Injection, Command Injection, path traversal, or unsanitized user input.
4. Insecure direct object references, broken access control, or authentication issues.
5. Insecure library usage or known vulnerable patterns.

IGNORE standard style guidelines, missing documentation, or logic bugs that do not have security implications.

{format_instructions}

PR Diff content to analyze:
{diff}

ChromaDB Context (Related Code):
{context}

Respond strictly in the requested JSON format. If you find no security issues, return a JSON object with an empty findings list: {{"findings": []}}.
"""

async def run_security(state: ReviewState) -> str:
    """
    Security Agent: Analyzes the PR diff and ChromaDB context for security issues,
    enforcing a strict JSON format.
    """
    print("[AGENT] Security Agent scanning diff...")
    
    # Check if security keys exist
    if not config.OPENROUTER_API_KEY:
        print("[AGENT] OPENROUTER_API_KEY is not configured. Returning empty security findings.")
        return json.dumps({"findings": []})

    # Prepare LLM client
    llm = ChatOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        model=config.SECURITY_MODEL,
        default_headers={
            "HTTP-Referer": "https://github.com/murali19980/OpenReview",
            "X-Title": "OpenReview Security Agent"
        },
        temperature=0.0 # Strict parsing requires low temperature
    )

    # Prepare prompt
    prompt = PromptTemplate(
        template=SECURITY_PROMPT_TEMPLATE,
        input_variables=["diff", "context"],
        partial_variables={"format_instructions": security_parser.get_format_instructions()}
    )

    diff_content = state.get("diff", "")
    context_content = state.get("retrieved_context", "No context available.")
    
    formatted_prompt = prompt.format(diff=diff_content, context=context_content)
    
    try:
        response = await llm.ainvoke(formatted_prompt)
        raw_output = response.content.strip()
        
        # Clean markdown wrappers (e.g. ```json ... ```) if present
        if raw_output.startswith("```"):
            lines = raw_output.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                raw_output = "\n".join(lines[1:-1]).strip()
        
        # Attempt to parse to validate JSON structure
        parsed_report = security_parser.parse(raw_output)
        print(f"[AGENT] Security Agent found {len(parsed_report.findings)} issue(s).")
        return json.dumps(parsed_report.dict(), indent=2)
        
    except Exception as e:
        print(f"[ERROR] Security Agent failed to run or parse output: {str(e)}")
        # Provide fallback empty structure
        return json.dumps({"findings": [{"file": "PR Diff", "line": "N/A", "severity": "LOW", "description": f"Failed to run security analysis or parse output: {str(e)}"}]})
