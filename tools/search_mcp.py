import os
import re
from contextlib import asynccontextmanager
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import config

@asynccontextmanager
async def get_search_mcp_session():
    """
    Context manager to safely launch the Brave Search MCP server,
    yield the session, and guarantee process termination on exit.
    """
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if not brave_api_key:
        raise ValueError("BRAVE_API_KEY is not configured in environment variables.")

    # Windows requires npx.cmd for subprocess execution
    command = "npx.cmd" if os.name == "nt" else "npx"
    
    server_params = StdioServerParameters(
        command=command,
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={
            **os.environ,
            "BRAVE_API_KEY": brave_api_key
        }
    )
    
    print("[MCP] Launching Brave Search MCP server process...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            try:
                yield session
            finally:
                print("[MCP] Closing Brave Search MCP session and terminating server process...")

async def fallback_search_ddg(query: str) -> str:
    """
    Fallback search using DuckDuckGo HTML parsing.
    Runs when Brave API key is missing or the MCP server fails.
    """
    print(f"[SEARCH] Running DuckDuckGo HTTP fallback search for: '{query}'")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    # DuckDuckGo HTML search URL
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code != 200:
                return f"DuckDuckGo search failed with HTTP status code {response.status_code}."
            
            html = response.text
            results = []
            
            # Extract result bodies from the simple HTML page
            # Typically structure is: <div class="result__body"> ... </div>
            blocks = re.findall(r'<div class="result__body">.*?</div>\s*</div>', html, re.DOTALL)
            
            for block in blocks[:5]:  # Return top 5 results
                # Find result title / link
                title_match = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
                url_match = re.search(r'<a class="result__url"[^>]*>(.*?)</a>', block, re.DOTALL)
                
                # Strip HTML tags
                snippet = re.sub(r'<[^>]*>', '', title_match.group(1)).strip() if title_match else ""
                url_text = re.sub(r'<[^>]*>', '', url_match.group(1)).strip() if url_match else ""
                
                if snippet:
                    results.append(f"- **{url_text or 'Result'}**: {snippet}")
            
            if not results:
                return "No search results found."
                
            return "\n".join(results)
            
    except Exception as e:
        print(f"[WARNING] DuckDuckGo fallback search failed: {str(e)}")
        return f"Web search failed: {str(e)}"

async def search_web(query: str) -> str:
    """
    Searches the web for security vulnerabilities (CVEs), package details, or docs.
    Attempts to use Brave Search MCP if configured; falls back to DuckDuckGo HTTP search otherwise.
    """
    brave_api_key = os.getenv("BRAVE_API_KEY")
    
    if not brave_api_key:
        print("[SEARCH] BRAVE_API_KEY not found in environment. Using DuckDuckGo fallback.")
        return await fallback_search_ddg(query)
        
    try:
        async with get_search_mcp_session() as session:
            print(f"[MCP] Invoking brave_web_search for: '{query}'")
            result = await session.call_tool(
                "brave_web_search",
                arguments={"query": query}
            )
            # Format and return results
            # The result is expected to be returned in standard MCP format
            # containing text content
            content_list = getattr(result, "content", [])
            output_texts = []
            for item in content_list:
                text = getattr(item, "text", "")
                if text:
                    output_texts.append(text)
            return "\n".join(output_texts) if output_texts else "No search results content found."
            
    except Exception as e:
        print(f"[WARNING] Brave Search MCP failed: {str(e)}. Falling back to DuckDuckGo.")
        return await fallback_search_ddg(query)
