import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base project path
BASE_DIR = Path(__file__).resolve().parent

# API Keys & Credentials
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# ChromaDB path defaults to standard location in local data folder
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "chromadb"))

# Server settings
PORT = int(os.getenv("PORT", "8000"))

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Target models on OpenRouter (using free models as primary, fallback as needed)
# Llama 3 8B Instruct (Free), Gemma 2 9B (Free), or Mistral 7B Instruct (Free)
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "meta-llama/llama-3-8b-instruct:free")
SECURITY_MODEL = os.getenv("SECURITY_MODEL", "meta-llama/llama-3-8b-instruct:free")
LOGIC_MODEL = os.getenv("LOGIC_MODEL", "google/gemma-2-9b-it:free")
DOCS_MODEL = os.getenv("DOCS_MODEL", "meta-llama/llama-3-8b-instruct:free")

# Validation check to assist developer troubleshooting on start
def validate_config():
    missing = []
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not GITHUB_PERSONAL_ACCESS_TOKEN:
        missing.append("GITHUB_PERSONAL_ACCESS_TOKEN")
    
    if missing:
        print(f"[WARNING] Config validation: Missing environment variables: {', '.join(missing)}")
        print("Please check your .env file or environment variables to configure them.")
    else:
        print("[INFO] Configuration validated successfully.")

validate_config()
