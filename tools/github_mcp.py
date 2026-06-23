import os
import sys
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import config

@asynccontextmanager
async def get_github_mcp_session():
    """
    Context manager to safely launch the GitHub MCP server, yield the session,
    and guarantee that the subprocess is cleaned up on exit or exception.
    """
    if not config.GITHUB_PERSONAL_ACCESS_TOKEN:
        raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN is not configured in environment variables.")

    # Determine command based on platform (Windows requires npx.cmd for subprocess execution)
    command = "npx.cmd" if os.name == "nt" else "npx"
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-github"],
        env={
            **os.environ,
            "GITHUB_PERSONAL_ACCESS_TOKEN": config.GITHUB_PERSONAL_ACCESS_TOKEN
        }
    )
    
    print("[MCP] Launching GitHub MCP server process...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            try:
                yield session
            finally:
                print("[MCP] Closing GitHub MCP session and terminating server process...")

async def post_pr_comment(repo_owner: str, repo_name: str, pr_number: int, body: str) -> Dict = None:
    """
    Posts the final code review report as a comment on the specified Pull Request.
    Utilizes the 'add_issue_comment' tool from the GitHub MCP server.
    """
    print(f"[MCP] Posting PR comment to {repo_owner}/{repo_name} #{pr_number}...")
    
    try:
        async with get_github_mcp_session() as session:
            # Call add_issue_comment tool which operates on Pull Requests
            result = await session.call_tool(
                "add_issue_comment",
                arguments={
                    "owner": repo_owner,
                    "repo": repo_name,
                    "number": int(pr_number),
                    "body": body
                }
            )
            print("[MCP] Successfully posted review comment to PR.")
            return result
    except Exception as e:
        print(f"[ERROR] Failed to post review comment via GitHub MCP: {str(e)}")
        # Raise error so workflow knows post failed
        raise e
