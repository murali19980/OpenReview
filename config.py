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

# Helper to strictly enforce and select OpenRouter models containing ':free'
def get_validated_free_model(env_var_name: str, fallback_default: str) -> str:
    model_val = os.getenv(env_var_name, fallback_default)
    if ":free" not in model_val:
        print(f"[WARNING] Model config '{model_val}' for {env_var_name} does not contain ':free'. "
              f"Enforcing and returning fallback: '{fallback_default}'")
        return fallback_default
    return model_val

PRIMARY_MODEL = get_validated_free_model("PRIMARY_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
SECURITY_MODEL = get_validated_free_model("SECURITY_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
LOGIC_MODEL = get_validated_free_model("LOGIC_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
DOCS_MODEL = get_validated_free_model("DOCS_MODEL", "meta-llama/llama-3.2-3b-instruct:free")

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
