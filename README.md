# OpenReview 🔍🤖

OpenReview is an **Automated Agentic Code Review System** powered by multiple specialist LLM agents orchestrated via **LangGraph**, using cost-effective free-tier models from **OpenRouter** (such as Llama 3 8B and Gemma 2 9B). It connects to your GitHub Pull Requests using the **Model Context Protocol (MCP)**, analyzes diffs, performs semantic code lookups in **ChromaDB**, and posts a unified code review report directly as a PR comment.

---

## 🛠️ Architecture & Workflow

OpenReview is structured as a stateful multi-agent state machine that coordinates execution through standard LangGraph parallel routing:

```
                  [ PR Webhook Event ]
                           │
                           ▼
                  ┌─────────────────┐
                  │  Triage Agent   │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐ (Parallel Routing)
             ▼             ▼             ▼
      ┌────────────┐┌────────────┐┌────────────┐
      │  Security  ││   Logic    ││   Docs     │
      │   Agent    ││   Agent    ││   Agent    │
      └──────┬─────┘└─────┬──────┘└─────┬──────┘
             │             │             │
             └─────────────┼─────────────┘ (Join Phase)
                           │
                           ▼
                  ┌─────────────────┐
                  │  Orchestrator   │
                  └────────┬────────┘
                           │
                           ▼
              [ Submit Comment to GitHub ]
```

### Specialist Agents
1. **Triage Agent**: Inspects changed files and the PR diff to determine the scope of reviews needed, dynamically turning specialized agents on or off.
2. **Security Agent**: Checks code for hardcoded secrets, security misconfigurations, and OWASP Top 10 vulnerabilities.
3. **Logic Agent**: Analyzes code logic, concurrency issues, edge cases, and optimization spots using Chain-of-Thought (CoT) reasoning.
4. **Docs Agent**: Checks for missing documentation, summarizes changes, and proposes README updates.
5. **Orchestrator Agent**: Aggregates the structured findings from specialists and formats them into a single, clean markdown PR review comment.

---

## ⚙️ Tech Stack
- **Framework**: [LangGraph](https://github.com/langchain-ai/langgraph) (Python)
- **LLM Provider**: [OpenRouter](https://openrouter.ai/) (supporting Llama 3 8B, Gemma 2, Mistral 7B)
- **External Integration**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for GitHub integration & Web Search
- **Memory**: [ChromaDB](https://github.com/chroma-core/chroma) for codebase semantic memory and episodic past PR reviews
- **Server**: FastAPI & Uvicorn for Webhook events

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10+
- `node` & `npx` (for running the GitHub MCP server)
- GitHub Personal Access Token (PAT) with `repo` scope

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/murali19980/OpenReview.git
cd OpenReview
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your details:
```bash
cp .env.example .env
```

Edit the `.env` file:
```ini
# OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_api_key_here

# GitHub Personal Access Token
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_pat_here

# ChromaDB Storage Path
CHROMA_DB_PATH=./data/chromadb

# Webhook secret to verify requests
WEBHOOK_SECRET=your_webhook_secret
```

### 4. Running the Webhook Server
Start the local review server:
```bash
uvicorn main:app --reload --port 8000
```
Use a tool like `ngrok` or similar to expose port `8000` to the internet and register it as a Webhook URL in your GitHub repository setting (`pull_request` events).

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
