import hmac
import hashlib
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import config
from graph.workflow import app as workflow_app
from tools.github_mcp import post_pr_comment
from memory.chroma_memory import get_relevant_context

app = FastAPI(title="OpenReview Webhook Server", version="1.0.0")

async def verify_signature(request: Request) -> bool:
    """
    Verifies that the webhook payload matches the signature sent by GitHub
    using the shared GITHUB_WEBHOOK_SECRET.
    """
    if not config.WEBHOOK_SECRET:
        print("[WARNING] WEBHOOK_SECRET is not configured. Webhook signature verification bypassed.")
        return True
        
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="X-Hub-Signature-256 header missing")
        
    body = await request.body()
    
    try:
        sha_name, signature = signature_header.split("=")
        if sha_name != "sha256":
            raise HTTPException(status_code=501, detail="Unsupported signature algorithm")
            
        mac = hmac.new(
            config.WEBHOOK_SECRET.encode(),
            msg=body,
            digestmod=hashlib.sha256
        )
        
        if not hmac.compare_digest(mac.hexdigest(), signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
            
        return True
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature parsing error: {str(e)}")

async def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """
    Fetches the raw text diff for the specified Pull Request using the GitHub API.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {config.GITHUB_PERSONAL_ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "OpenReview-App"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text

async def get_pr_files(owner: str, repo: str, pr_number: int) -> List[str]:
    """
    Fetches the list of filenames changed in the specified Pull Request.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"token {config.GITHUB_PERSONAL_ACCESS_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OpenReview-App"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        files_data = response.json()
        return [item["filename"] for item in files_data]

async def process_pull_request_review(payload: Dict[str, Any]):
    """
    Background worker that runs the LangGraph multi-agent review workflow
    and posts the compiled summary back to the GitHub PR.
    """
    pr_number = payload["number"]
    repo_data = payload["repository"]
    repo_name = repo_data["name"]
    repo_owner = repo_data["owner"]["login"]
    pr_title = payload["pull_request"]["title"]
    pr_desc = payload["pull_request"].get("body") or ""
    
    print(f"\n[SERVER] Beginning code review for {repo_owner}/{repo_name} #{pr_number}: '{pr_title}'")
    
    try:
        # 1. Fetch code diff and file list
        pr_diff = await get_pr_diff(repo_owner, repo_name, pr_number)
        changed_files = await get_pr_files(repo_owner, repo_name, pr_number)
        
        # 2. Retrieve semantic context from ChromaDB
        print("[SERVER] Retrieving semantic code memory...")
        retrieved_context = get_relevant_context(changed_files, pr_diff)
        
        # 3. Build initial LangGraph state
        initial_state = {
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "pr_number": pr_number,
            "title": pr_title,
            "description": pr_desc,
            "diff": pr_diff,
            "changed_files": changed_files,
            "triage_decisions": {},
            "retrieved_context": retrieved_context,
            "security_findings": "",
            "logic_findings": "",
            "docs_findings": "",
            "final_report": "",
            "messages": []
        }
        
        # 4. Invoke LangGraph state machine
        print("[SERVER] Running LangGraph agentic workflow...")
        final_state = await workflow_app.ainvoke(initial_state)
        
        # 5. Extract compiled report and write back to GitHub PR via MCP
        final_report = final_state.get("final_report", "")
        if final_report:
            print("[SERVER] Review complete. Posting final report...")
            await post_pr_comment(repo_owner, repo_name, pr_number, final_report)
            print("[SERVER] Successfully completed and posted code review.")
        else:
            print("[WARNING] Orchestrator did not compile a final report.")
            
    except Exception as e:
        print(f"[ERROR] Error processing pull request review: {str(e)}")

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming webhook payloads from GitHub pull_request events.
    Verifies signatures and triggers review pipeline in the background.
    """
    # 1. Verify webhook signature
    await verify_signature(request)
    
    # 2. Parse event type
    github_event = request.headers.get("X-GitHub-Event")
    if github_event != "pull_request":
        raise HTTPException(status_code=400, detail=f"Unsupported event type: {github_event}")
        
    payload = await request.json()
    action = payload.get("action")
    
    # We only process PRs when opened or updated
    if action not in ("opened", "synchronize"):
        print(f"[SERVER] Webhook ignored action: '{action}'")
        return {"status": "ignored", "action": action}
        
    # Run the orchestration flow in the background to return 200 quickly to GitHub
    background_tasks.add_task(process_pull_request_review, payload)
    
    return {"status": "queued", "message": "Review processing started in background."}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
