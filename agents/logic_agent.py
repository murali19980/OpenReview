from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import config
from graph.state import ReviewState

# System prompt for Logic Agent enforcing Chain-of-Thought (<thinking>) and findings (<bug_report>)
LOGIC_PROMPT_TEMPLATE = """
You are a Senior Software Architect and Principal Logic/Quality Assurance Engineer.
Your job is to identify bugs, logical errors, edge cases, off-by-one errors, performance issues, resource leaks (like unclosed connections/files), and async/concurrency issues in the pull request code diff.

### Instructions:
1. You MUST use Chain-of-Thought reasoning.
2. Structure your output exactly like this:
   <thinking>
   Write your detailed step-by-step reasoning here. Review the code line-by-line. Think about what could go wrong, corner cases, null pointers, type issues, race conditions, or performance bottlenecks.
   </thinking>
   <bug_report>
   ### Logic Review Findings
   - **File**: <file_name>
     **Line**: <line_number>
     **Issue**: <brief_description>
     **Detail**: <reproduction_steps_or_reasoning>
     **Recommendation**: <how_to_fix_it>
   (If no logic issues are found, state: "No logical bugs or issues detected.")
   </bug_report>

3. Focus ONLY on functional correctness, logic, performance, and robustness. Do not review code formatting, missing docs, or security vulnerabilities (which are handled by other agents).

PR Diff content to analyze:
{diff}

ChromaDB Context (Related codebase structures):
{context}
"""

async def run_logic(state: ReviewState) -> str:
    """
    Logic Agent: Analyzes code diffs for functional bugs and logic flaws.
    Uses Chain-of-Thought (<thinking>) blocks to improve reasoning accuracy on free models.
    """
    print("[AGENT] Logic Agent checking diff for bugs...")
    
    if not config.OPENROUTER_API_KEY:
        print("[AGENT] OPENROUTER_API_KEY is not configured. Returning empty logic report.")
        return "<thinking>\nNo API key.\n</thinking>\n<bug_report>\nNo logical bugs or issues detected.\n</bug_report>"

    # Prepare LLM client
    llm = ChatOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        model=config.LOGIC_MODEL,
        default_headers={
            "HTTP-Referer": "https://github.com/murali19980/OpenReview",
            "X-Title": "OpenReview Logic Agent"
        },
        temperature=0.1
    )

    prompt = PromptTemplate(
        template=LOGIC_PROMPT_TEMPLATE,
        input_variables=["diff", "context"]
    )

    diff_content = state.get("diff", "")
    context_content = state.get("retrieved_context", "No context available.")
    
    formatted_prompt = prompt.format(diff=diff_content, context=context_content)
    
    try:
        response = await llm.ainvoke(formatted_prompt)
        raw_output = response.content.strip()
        
        # Verify if tags are present. If not, log a warning but return content.
        if "<thinking>" not in raw_output or "<bug_report>" not in raw_output:
            print("[WARNING] Logic Agent response did not strictly follow the <thinking> and <bug_report> tags convention.")
            
        print("[AGENT] Logic Agent analysis complete.")
        return raw_output
        
    except Exception as e:
        print(f"[ERROR] Logic Agent execution failed: {str(e)}")
        return f"<thinking>\nExecution failed.\n</thinking>\n<bug_report>\nError running logic review: {str(e)}\n</bug_report>"
