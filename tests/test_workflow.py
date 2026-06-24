import asyncio
import sys
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows consoles to prevent charmap encoding errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add parent directory to path so we can import from agents, graph, and tools
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from graph.workflow import app as workflow_app

# Define a simulated PR Diff containing deliberate bugs:
# 1. Hardcoded API secrets (Security Agent target)
# 2. Potential division by zero logic bug (Logic Agent target)
# 3. Missing documentation on a new function (Docs Agent target)
DUMMY_DIFF = """
diff --git a/auth_service.py b/auth_service.py
index e69de29..7ba8642 100644
--- a/auth_service.py
+++ b/auth_service.py
@@ -1,15 +1,28 @@
 import os
 import requests
 
+# Deliberate Security Issue: Hardcoded administrative API credential
+ADMIN_API_KEY = "sk-proj-fake-live-secret-key-1a2b3c4d5e"
+
 def login_user(username, password):
     print(f"Attempting login for user: {username}")
     # Authentication logic placeholder
     return True
 
+# Deliberate Docs Issue: Missing docstring and parameter descriptions
+def calculate_user_allowance(user_id, balance, rate_limit_days):
+    # Deliberate Logic Bug: Division by zero risk if rate_limit_days is 0
+    daily_allowance = balance / rate_limit_days
+    return daily_allowance
+
 def get_service_status():
     url = "https://api.internal.service/health"
+    # Using the hardcoded secret
+    headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}
     response = requests.get(url, headers=headers)
     return response.json()
diff --git a/docs/README.md b/docs/README.md
index a12345b..b67890c 100644
--- a/docs/README.md
+++ b/docs/README.md
@@ -1,4 +1,6 @@
 # Internal Auth Services
 
-This directory handles user login.
+This directory handles user login and authentication tokens.
+
+## Allowance Calculation
+Added allowance calculations based on user history and rate periods.
"""

async def run_local_verification():
    """
    Simulates the LangGraph agent review workflow locally using a dummy diff.
    Prints the final orchestrated markdown review to the terminal.
    """
    print("=" * 60)
    print("STARTING OPENREVIEW LOCAL WORKFLOW VERIFICATION")
    print("=" * 60)
    
    # 1. Setup simulated initial state
    initial_state: Dict[str, Any] = {
        "repo_owner": "murali19980",
        "repo_name": "OpenReview",
        "pr_number": 42,
        "title": "feat: Add allowance calculator and secret config",
        "description": "Introduces user allowance metrics and binds admin secret token.",
        "diff": DUMMY_DIFF,
        "changed_files": ["auth_service.py", "docs/README.md"],
        "triage_decisions": {},
        "retrieved_context": "--- Reference Context Match ---\nFile: auth_service.py\nContent:\ndef login_user(username, password):\n    return True\n",
        "security_findings": "",
        "logic_findings": "",
        "docs_findings": "",
        "final_report": "",
        "messages": []
    }
    
    print("\n[TEST] Invoking LangGraph workflow with simulated initial state...")
    try:
        # 2. Run LangGraph workflow asynchronously
        final_state = await workflow_app.ainvoke(initial_state)
        
        # 3. Print compiled report
        print("\n" + "=" * 60)
        print("FINAL COMPILED REVIEW REPORT (ORCHESTRATOR)")
        print("=" * 60)
        print(final_state.get("final_report", "No report compiled."))
        print("=" * 60)
        
        # Print intermediate state logs for debugging
        print("\nTriage Decisions:", final_state.get("triage_decisions"))
        print("Security findings length:", len(final_state.get("security_findings", "")))
        print("Logic findings length:", len(final_state.get("logic_findings", "")))
        print("Docs findings length:", len(final_state.get("docs_findings", "")))
        
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_local_verification())
