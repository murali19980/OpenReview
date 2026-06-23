import os
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
import config

# Global client and collection placeholders
_client = None
_collection = None

def get_chroma_resources():
    """
    Helper to lazily initialize the ChromaDB client and collection.
    Ensures that the directory exists and handles initialization errors gracefully.
    """
    global _client, _collection
    if _collection is not None:
        return _client, _collection

    try:
        # Create persistent storage directory if it doesn't exist
        os.makedirs(config.CHROMA_DB_PATH, exist_ok=True)
        
        # Initialize persistent client
        _client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        
        # Get or create the codebase context collection
        # Uses ChromaDB's default embedding model (SentenceTransformers all-MiniLM-L6-v2)
        _collection = _client.get_or_create_collection(
            name="codebase_context",
            metadata={"hnsw:space": "cosine"} # Using cosine similarity for code matching
        )
        print(f"[MEMORY] ChromaDB initialized at: {config.CHROMA_DB_PATH}")
        return _client, _collection
    except Exception as e:
        print(f"[ERROR] Failed to initialize ChromaDB: {str(e)}")
        return None, None

def index_code_snippet(file_path: str, chunk_content: str, metadata: dict) -> bool:
    """
    Indexes a single code chunk/snippet into the ChromaDB codebase_context collection.
    """
    _, collection = get_chroma_resources()
    if collection is None:
        print("[WARNING] ChromaDB is not initialized. Skipping indexing.")
        return False
        
    try:
        # Generate a unique ID based on file path and a simple hash/length
        snippet_id = f"{file_path}_{hash(chunk_content)}_{len(chunk_content)}"
        
        # Merge basic metadata
        final_metadata = {
            **metadata,
            "file_path": file_path
        }
        
        collection.add(
            documents=[chunk_content],
            metadatas=[final_metadata],
            ids=[snippet_id]
        )
        return True
    except Exception as e:
        print(f"[ERROR] Failed to index code snippet for {file_path}: {str(e)}")
        return False

def get_relevant_context(file_paths: List[str], diff_snippet: str) -> str:
    """
    Queries ChromaDB using the PR diff snippet to find the most similar existing
    code blocks in the repository.
    """
    _, collection = get_chroma_resources()
    if collection is None:
        print("[WARNING] ChromaDB is not initialized. Returning empty context.")
        return ""
        
    try:
        # Check if collection is empty
        count = collection.count()
        if count == 0:
            print("[MEMORY] ChromaDB codebase_context collection is empty. No context retrieved.")
            return ""
            
        print(f"[MEMORY] Querying ChromaDB with diff snippet ({len(diff_snippet)} chars)...")
        # Query the database
        results = collection.query(
            query_texts=[diff_snippet],
            n_results=min(3, count), # Retrieve top 3 or less depending on db size
        )
        
        # Format the retrieved code snippets
        formatted_results = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        for idx, (doc, meta) in enumerate(zip(documents, metadatas)):
            src_file = meta.get("file_path", "Unknown File")
            formatted_results.append(
                f"--- Reference Code Match #{idx + 1} ---\n"
                f"File: {src_file}\n"
                f"Content:\n{doc}\n"
            )
            
        if not formatted_results:
            return ""
            
        print(f"[MEMORY] Successfully retrieved {len(formatted_results)} reference code blocks from ChromaDB.")
        return "\n".join(formatted_results)
        
    except Exception as e:
        print(f"[ERROR] Failed to query ChromaDB: {str(e)}")
        return ""
