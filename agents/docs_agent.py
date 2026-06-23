from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import config
from graph.state import ReviewState

DOCS_PROMPT_TEMPLATE = """
You are a Technical Writer and Senior Developer.
Your job is to generate documentation summaries for the code changed in the pull request, check if updates are needed for README, and point out missing docstrings or comments.

Analyze the PR code changes and output:
1. A concise bulleted **Summary of Changes**.
2. **Documentation Gaps**: Any public classes, methods, or functions that are missing necessary docstrings, type annotations, or clarifying comments.
3. **Docs/README updates**: Recommendations on how this affects consumer docs or if the project's README needs updates.

Output in clean, structured Markdown format. If no gaps are found and no doc updates are needed, write: "Documentation is fully complete and up to date."

PR Diff content:
{diff}
"""

async def run_docs(state: ReviewState) -> str:
    """
    Docs Agent: Analyzes code changes for docstrings, missing documentation,
    and summarizes modifications in Markdown.
    """
    print("[AGENT] Docs Agent analyzing diff for documentation needs...")
    
    if not config.OPENROUTER_API_KEY:
        print("[AGENT] OPENROUTER_API_KEY is not configured. Returning empty docs summary.")
        return "No documentation issues detected."

    # Prepare LLM client
    llm = ChatOpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        model=config.DOCS_MODEL,
        default_headers={
            "HTTP-Referer": "https://github.com/murali19980/OpenReview",
            "X-Title": "OpenReview Docs Agent"
        },
        temperature=0.2
    )

    prompt = PromptTemplate(
        template=DOCS_PROMPT_TEMPLATE,
        input_variables=["diff"]
    )

    diff_content = state.get("diff", "")
    formatted_prompt = prompt.format(diff=diff_content)
    
    try:
        response = await llm.ainvoke(formatted_prompt)
        print("[AGENT] Docs Agent analysis complete.")
        return response.content.strip()
        
    except Exception as e:
        print(f"[ERROR] Docs Agent execution failed: {str(e)}")
        return f"Error running docs review: {str(e)}"
